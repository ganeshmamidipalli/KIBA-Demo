#!/usr/bin/env python3
"""
Post-Cart Phase Service
Handles G1 decision gate evaluation, PR creation, RFQ management, and approval workflows
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class ApproverRole(Enum):
    PMO = "PMO"
    EVP = "EVP"
    Finance = "Finance"
    Contracts = "Contracts"
    President = "President"

class ProcurementType(Enum):
    CC_APPROVED_SPEND_PLAN = "CC_APPROVED_SPEND_PLAN"
    CC_NOT_IN_SPEND_PLAN = "CC_NOT_IN_SPEND_PLAN"
    PROC_COMPETITIVE = "PROC_COMPETITIVE"
    PROC_SOLE_SOURCE = "PROC_SOLE_SOURCE"
    BIDS_AND_PROPOSALS = "BIDS_AND_PROPOSALS"
    ROMS = "ROMS"

@dataclass
class LineItem:
    sku: str
    desc: str
    qty: int
    uom: str
    unitPrice: float
    currency: str
    leadDays: int
    deliveryTerms: Optional[str] = None
    quoteValidity: Optional[str] = None

@dataclass
class VendorRef:
    id: str
    name: str
    contact: str
    website: Optional[str] = None

@dataclass
class DocRef:
    type: str  # 'Quote' | 'RFQ' | 'Comparison' | 'SSJ' | 'CoverSheet' | 'Spec' | 'Other'
    url: str
    filename: str
    hash: str
    uploadedAt: str

@dataclass
class Justification:
    type: str  # 'SSJ' | 'Budgeted' | 'Technical' | 'Other'
    text: Optional[str] = None
    amount: Optional[float] = None

@dataclass
class ApproverAssignment:
    role: str
    userId: str
    name: str
    email: str

@dataclass
class ApproverDecision:
    role: str
    userId: str
    decision: str  # 'APPROVED' | 'REJECTED' | 'REQUEST_CHANGES'
    timestamp: str
    comment: Optional[str] = None

@dataclass
class ApprovalRoute:
    required: List[str]
    roster: List[ApproverAssignment]
    decisions: List[ApproverDecision]

@dataclass
class AuditEntry:
    actor: str
    action: str
    timestamp: str
    delta: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None

@dataclass
class PR:
    id: str
    projectKeys: List[str]
    spendType: str  # 'Direct' | 'Indirect'
    budgeted: bool
    estimatedCost: float
    competitive: bool
    justification: Optional[Justification]
    vendor: VendorRef
    lineItems: List[LineItem]
    documents: List[DocRef]
    approvals: ApprovalRoute
    status: str  # 'PR_DRAFT' | 'PR_SUBMITTED' | 'APPROVALS_IN_FLIGHT' | 'APPROVED' | 'PO_ISSUED' | 'REWORK'
    audit: List[AuditEntry]
    createdAt: str
    updatedAt: str

@dataclass
class VendorRFQ:
    vendorId: str
    vendorName: str
    contact: str
    status: str  # 'PENDING' | 'SENT' | 'RECEIVED' | 'WITHDRAWN'
    sentAt: Optional[str] = None
    receivedAt: Optional[str] = None

@dataclass
class RFQ:
    id: str
    prCandidateId: Optional[str]
    vendors: List[VendorRFQ]
    dueDate: str
    status: str  # 'RFQ_PREP' | 'RFQ_SENT' | 'RFQ_RESPONSES' | 'VENDOR_EVAL' | 'SELECTION_FINALIZED'
    audit: List[AuditEntry]
    createdAt: str
    updatedAt: str

@dataclass
class G1Context:
    selectedVendors: List[Dict[str, Any]]
    items: List[LineItem]
    pricing: Dict[str, List[LineItem]]
    procurementContext: Dict[str, Any]

@dataclass
class G1Result:
    passed: bool
    reasonCodes: List[str]
    missingItems: List[str]
    recommendations: List[str]
    requiredApprovers: List[str]

@dataclass
class ChecklistItem:
    id: str
    label: str
    status: str  # 'PASS' | 'FAIL' | 'WARNING'
    message: Optional[str] = None
    required: bool = True

@dataclass
class CartDecision:
    recommendation: str  # 'PROCEED_TO_APPROVALS' | 'GENERATE_RFQS'
    reason: str
    g1Result: G1Result
    readinessPercentage: float
    checklist: List[ChecklistItem]

class G1RuleEngine:
    """Decision Gate G1 Rule Engine for procurement readiness evaluation"""
    
    PRICING_THRESHOLDS = {
        'CC_PMO_THRESHOLD': 5000,
        'CC_FINANCE_THRESHOLD': 5000,
        'PROC_PRESIDENT_THRESHOLD': 250000,
        'ROMS_FINANCE_THRESHOLD': 250000,
        'ROMS_PRESIDENT_THRESHOLD': 500000,
        'SSJ_CONTRACTS_THRESHOLD': 250000
    }

    @staticmethod
    def evaluate(context: G1Context) -> G1Result:
        """Main G1 evaluation function"""
        selected_vendors = context.selectedVendors
        items = context.items
        pricing = context.pricing
        procurement_context = context.procurementContext
        
        reason_codes = []
        missing_items = []
        recommendations = []
        required_approvers = []

        # 1. Pricing Completeness Check
        pricing_check = G1RuleEngine._check_pricing_completeness(selected_vendors, items, pricing)
        if not pricing_check['pass']:
            reason_codes.extend(pricing_check['reasonCodes'])
            missing_items.extend(pricing_check['missingItems'])

        # 2. Document Sufficiency Check
        doc_check = G1RuleEngine._check_document_sufficiency(selected_vendors, items)
        if not doc_check['pass']:
            reason_codes.extend(doc_check['reasonCodes'])
            missing_items.extend(doc_check['missingItems'])

        # 3. Business Rules Check
        business_check = G1RuleEngine._check_business_rules(procurement_context)
        if not business_check['pass']:
            reason_codes.extend(business_check['reasonCodes'])
            recommendations.extend(business_check['recommendations'])

        # 4. Determine Required Approvers
        approvers = G1RuleEngine._resolve_approvers(procurement_context)
        required_approvers.extend(approvers['required'])

        # 5. Final Decision
        pass_result = len(reason_codes) == 0 and len(missing_items) == 0
        
        if not pass_result:
            recommendations.append('Consider generating RFQs to gather missing information')

        return G1Result(
            passed=pass_result,
            reasonCodes=reason_codes,
            missingItems=missing_items,
            recommendations=recommendations,
            requiredApprovers=required_approvers
        )

    @staticmethod
    def generate_cart_decision(context: G1Context) -> CartDecision:
        """Generate cart decision with checklist"""
        g1_result = G1RuleEngine.evaluate(context)
        checklist = G1RuleEngine._generate_checklist(context, g1_result)
        readiness_percentage = G1RuleEngine._calculate_readiness_percentage(checklist)
        
        recommendation = 'PROCEED_TO_APPROVALS' if g1_result.passed else 'GENERATE_RFQS'
        reason = (
            'All requirements met for direct procurement approval' if g1_result.passed
            else f"Missing items: {', '.join(g1_result.missingItems)}"
        )

        return CartDecision(
            recommendation=recommendation,
            reason=reason,
            g1Result=g1_result,
            readinessPercentage=readiness_percentage,
            checklist=checklist
        )

    @staticmethod
    def _check_pricing_completeness(vendors, items, pricing):
        """Check pricing completeness for all selected vendors"""
        reason_codes = []
        missing_items = []

        for vendor in vendors:
            vendor_pricing = pricing.get(vendor['id'], [])
            
            if not vendor_pricing:
                reason_codes.append('MISSING_PRICE')
                missing_items.append(f"No pricing available for {vendor['name']}")
                continue

            for item in items:
                vendor_item = next((p for p in vendor_pricing if p.sku == item.sku), None)
                if not vendor_item:
                    reason_codes.append('MISSING_PRICE')
                    missing_items.append(f"Missing price for {item.desc} from {vendor['name']}")
                    continue

                if not vendor_item.unitPrice or vendor_item.unitPrice <= 0:
                    reason_codes.append('INVALID_PRICE')
                    missing_items.append(f"Invalid unit price for {item.desc} from {vendor['name']}")

                if not vendor_item.currency:
                    reason_codes.append('MISSING_CURRENCY')
                    missing_items.append(f"Missing currency for {item.desc} from {vendor['name']}")

                if not vendor_item.leadDays or vendor_item.leadDays <= 0:
                    reason_codes.append('MISSING_LEAD_TIME')
                    missing_items.append(f"Missing lead time for {item.desc} from {vendor['name']}")

                if not vendor_item.deliveryTerms:
                    reason_codes.append('MISSING_DELIVERY_TERMS')
                    missing_items.append(f"Missing delivery terms for {item.desc} from {vendor['name']}")

                if not vendor_item.quoteValidity:
                    reason_codes.append('MISSING_QUOTE_VALIDITY')
                    missing_items.append(f"Missing quote validity for {item.desc} from {vendor['name']}")

        return {
            'pass': len(reason_codes) == 0,
            'reasonCodes': reason_codes,
            'missingItems': missing_items
        }

    @staticmethod
    def _check_document_sufficiency(vendors, items):
        """Check document sufficiency"""
        reason_codes = []
        missing_items = []

        has_quote_evidence = any(v.get('contact') and v.get('website') for v in vendors)
        if not has_quote_evidence:
            reason_codes.append('INSUFFICIENT_EVIDENCE')
            missing_items.append('No quote evidence or vendor contact information')

        has_specs = any(item.desc and len(item.desc) > 10 for item in items)
        if not has_specs:
            reason_codes.append('INSUFFICIENT_SPECS')
            missing_items.append('Insufficient product specifications')

        return {
            'pass': len(reason_codes) == 0,
            'reasonCodes': reason_codes,
            'missingItems': missing_items
        }

    @staticmethod
    def _check_business_rules(context):
        """Check business rules compliance"""
        reason_codes = []
        recommendations = []

        if context.get('isSoleSource') and not context.get('ssjAmount'):
            reason_codes.append('SOLE_SOURCE_JUST_REQUIRED')
            recommendations.append('Sole source justification required for non-competitive procurement')

        if context.get('contractRequired') and not context.get('contractExecuted'):
            reason_codes.append('CONTRACT_REQUIRED')
            recommendations.append('Contract execution required before proceeding')

        if not context.get('budgeted') and context.get('spendPlanStatus') == 'NOT_IN_PLAN':
            reason_codes.append('UNBUDGETED_PROCUREMENT')
            recommendations.append('Unbudgeted procurement requires additional approvals')

        return {
            'pass': len(reason_codes) == 0,
            'reasonCodes': reason_codes,
            'recommendations': recommendations
        }

    @staticmethod
    def _resolve_approvers(context):
        """Resolve required approvers based on KMI matrix rules"""
        required = set()
        reasons = []

        procurement_type = context.get('procurementType')
        estimated_cost = context.get('estimatedCost', 0)

        if procurement_type == 'CC_APPROVED_SPEND_PLAN':
            return {'required': [], 'reasons': ['Approved spend plan – CC purchase']}

        elif procurement_type == 'CC_NOT_IN_SPEND_PLAN':
            if estimated_cost > G1RuleEngine.PRICING_THRESHOLDS['CC_PMO_THRESHOLD']:
                required.add('PMO')
                required.add('Finance')
                reasons.extend(['PMO: CC > $5k', 'Finance: CC > $5k'])

        elif procurement_type == 'PROC_COMPETITIVE':
            required.update(['PMO', 'EVP', 'Finance'])
            reasons.extend(['PMO: Competitive procurement', 'EVP: Policy', 'Finance: Policy'])
            
            if context.get('contractExecuted'):
                required.add('Contracts')
                reasons.append('Contracts: Executed by a contract')
            
            if estimated_cost > G1RuleEngine.PRICING_THRESHOLDS['PROC_PRESIDENT_THRESHOLD']:
                required.add('President')
                reasons.append('President: > $250k')

        elif procurement_type == 'PROC_SOLE_SOURCE':
            required.update(['PMO', 'EVP', 'Finance'])
            reasons.extend(['PMO: Sole source', 'EVP: Policy', 'Finance: Policy'])
            
            if context.get('contractExecuted') or context.get('ssjAmount', 0) > G1RuleEngine.PRICING_THRESHOLDS['SSJ_CONTRACTS_THRESHOLD']:
                required.add('Contracts')
                reasons.append('Contracts: Contract/SSJ > $250k')
            
            if estimated_cost > G1RuleEngine.PRICING_THRESHOLDS['PROC_PRESIDENT_THRESHOLD']:
                required.add('President')
                reasons.append('President: > $250k')

        elif procurement_type == 'BIDS_AND_PROPOSALS':
            required.update(['PMO', 'EVP', 'Finance'])
            reasons.extend(['PMO: B&P baseline', 'EVP: B&P baseline', 'Finance: B&P baseline'])
            
            if estimated_cost > G1RuleEngine.PRICING_THRESHOLDS['PROC_PRESIDENT_THRESHOLD']:
                required.add('President')
                reasons.append('President: > $250k')

        elif procurement_type == 'ROMS':
            required.update(['PMO', 'EVP'])
            reasons.extend(['PMO: ROMS', 'EVP: ROMS'])
            
            if estimated_cost > G1RuleEngine.PRICING_THRESHOLDS['ROMS_FINANCE_THRESHOLD']:
                required.add('Finance')
                reasons.append('Finance: ROMS > $250k')
            
            if estimated_cost > G1RuleEngine.PRICING_THRESHOLDS['ROMS_PRESIDENT_THRESHOLD']:
                required.add('President')
                reasons.append('President: ROMS > $500k')

        return {'required': list(required), 'reasons': reasons}

    @staticmethod
    def _generate_checklist(context, g1_result):
        """Generate checklist items for UI display"""
        checklist = []

        # Pricing completeness
        pricing_complete = not any(code in g1_result.reasonCodes for code in 
            ['MISSING_PRICE', 'INVALID_PRICE', 'MISSING_CURRENCY', 'MISSING_LEAD_TIME', 'MISSING_DELIVERY_TERMS', 'MISSING_QUOTE_VALIDITY'])
        checklist.append(ChecklistItem(
            id='pricing',
            label='Complete pricing for all vendors',
            status='PASS' if pricing_complete else 'FAIL',
            message='All vendors have complete pricing' if pricing_complete else 'Missing pricing information',
            required=True
        ))

        # Document sufficiency
        docs_sufficient = not any(code in g1_result.reasonCodes for code in 
            ['INSUFFICIENT_EVIDENCE', 'INSUFFICIENT_SPECS'])
        checklist.append(ChecklistItem(
            id='documents',
            label='Sufficient supporting documents',
            status='PASS' if docs_sufficient else 'FAIL',
            message='All required documents available' if docs_sufficient else 'Missing supporting documents',
            required=True
        ))

        # Business rules
        business_rules_pass = not any(code in g1_result.reasonCodes for code in 
            ['SOLE_SOURCE_JUST_REQUIRED', 'CONTRACT_REQUIRED', 'UNBUDGETED_PROCUREMENT'])
        checklist.append(ChecklistItem(
            id='business_rules',
            label='Business rules compliance',
            status='PASS' if business_rules_pass else 'FAIL',
            message='All business rules satisfied' if business_rules_pass else 'Business rule violations detected',
            required=True
        ))

        # Approver resolution
        approvers_resolved = len(g1_result.requiredApprovers) > 0
        checklist.append(ChecklistItem(
            id='approvers',
            label='Approver roster resolved',
            status='PASS' if approvers_resolved else 'WARNING',
            message=f"{len(g1_result.requiredApprovers)} approvers identified" if approvers_resolved else 'Approver resolution pending',
            required=True
        ))

        return checklist

    @staticmethod
    def _calculate_readiness_percentage(checklist):
        """Calculate readiness percentage based on checklist"""
        required_items = [item for item in checklist if item.required]
        passed_items = [item for item in required_items if item.status == 'PASS']
        return (len(passed_items) / len(required_items) * 100) if required_items else 0

class PostCartService:
    """Main service for Post-Cart phase operations"""
    
    def __init__(self):
        self.prs = {}  # In-memory storage for demo
        self.rfqs = {}  # In-memory storage for demo
        self.g1_engine = G1RuleEngine()

    def evaluate_g1(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate G1 decision gate"""
        try:
            # Convert context data to G1Context
            context = G1Context(
                selectedVendors=context_data['selectedVendors'],
                items=[LineItem(**item) for item in context_data['items']],
                pricing={k: [LineItem(**item) for item in v] for k, v in context_data['pricing'].items()},
                procurementContext=context_data['procurementContext']
            )
            
            # Generate decision
            decision = self.g1_engine.generate_cart_decision(context)
            
            # Convert to dict for JSON serialization
            return asdict(decision)
            
        except Exception as e:
            logger.error(f"Error evaluating G1: {e}")
            raise

    def create_pr(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new PR"""
        try:
            pr_id = f"PR-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
            
            # Create PR object
            pr = PR(
                id=pr_id,
                projectKeys=pr_data['projectKeys'],
                spendType=pr_data['spendType'],
                budgeted=pr_data['budgeted'],
                estimatedCost=pr_data['estimatedCost'],
                competitive=pr_data['competitive'],
                justification=Justification(**pr_data['justification']) if pr_data.get('justification') else None,
                vendor=VendorRef(**pr_data['vendor']),
                lineItems=[LineItem(**item) for item in pr_data['lineItems']],
                documents=[DocRef(**doc) for doc in pr_data.get('documents', [])],
                approvals=ApprovalRoute(
                    required=pr_data.get('approvals', {}).get('required', []),
                    roster=[],
                    decisions=[]
                ),
                status='PR_DRAFT',
                audit=[],
                createdAt=datetime.now().isoformat(),
                updatedAt=datetime.now().isoformat()
            )
            
            # Store PR
            self.prs[pr_id] = pr
            
            logger.info(f"Created PR {pr_id}")
            return asdict(pr)
            
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            raise

    def start_approval_routing(self, pr_id: str, approval_route: Dict[str, Any]) -> Dict[str, Any]:
        """Start approval routing for a PR"""
        try:
            if pr_id not in self.prs:
                raise ValueError(f"PR {pr_id} not found")
            
            pr = self.prs[pr_id]
            
            # Update approval route
            pr.approvals.required = approval_route['required']
            pr.status = 'APPROVALS_IN_FLIGHT'
            pr.updatedAt = datetime.now().isoformat()
            
            # Add audit entry
            pr.audit.append(AuditEntry(
                actor='system',
                action='APPROVAL_ROUTING_STARTED',
                timestamp=datetime.now().isoformat(),
                reason=f"Started approval routing for {len(approval_route['required'])} approvers"
            ))
            
            logger.info(f"Started approval routing for PR {pr_id}")
            return {'success': True, 'message': 'Approval routing started successfully'}
            
        except Exception as e:
            logger.error(f"Error starting approval routing: {e}")
            raise

    def generate_rfq(self, rfq_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a new RFQ"""
        try:
            rfq_id = f"RFQ-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
            
            # Create RFQ object
            rfq = RFQ(
                id=rfq_id,
                prCandidateId=rfq_data.get('prCandidateId'),
                vendors=[VendorRFQ(**vendor) for vendor in rfq_data['vendors']],
                dueDate=rfq_data['dueDate'],
                status='RFQ_PREP',
                audit=[],
                createdAt=datetime.now().isoformat(),
                updatedAt=datetime.now().isoformat()
            )
            
            # Store RFQ
            self.rfqs[rfq_id] = rfq
            
            logger.info(f"Generated RFQ {rfq_id}")
            return asdict(rfq)
            
        except Exception as e:
            logger.error(f"Error generating RFQ: {e}")
            raise

    def send_rfq(self, rfq_id: str) -> Dict[str, Any]:
        """Send RFQ to vendors"""
        try:
            if rfq_id not in self.rfqs:
                raise ValueError(f"RFQ {rfq_id} not found")
            
            rfq = self.rfqs[rfq_id]
            
            # Update vendor statuses
            for vendor in rfq.vendors:
                vendor.status = 'SENT'
                vendor.sentAt = datetime.now().isoformat()
            
            rfq.status = 'RFQ_SENT'
            rfq.updatedAt = datetime.now().isoformat()
            
            # Add audit entry
            rfq.audit.append(AuditEntry(
                actor='system',
                action='RFQ_SENT',
                timestamp=datetime.now().isoformat(),
                reason=f"Sent RFQ to {len(rfq.vendors)} vendors"
            ))
            
            logger.info(f"Sent RFQ {rfq_id} to {len(rfq.vendors)} vendors")
            return {'success': True, 'message': 'RFQ sent successfully'}
            
        except Exception as e:
            logger.error(f"Error sending RFQ: {e}")
            raise

    def get_pr_status(self, pr_id: str) -> Dict[str, Any]:
        """Get PR status"""
        try:
            if pr_id not in self.prs:
                raise ValueError(f"PR {pr_id} not found")
            
            return asdict(self.prs[pr_id])
            
        except Exception as e:
            logger.error(f"Error getting PR status: {e}")
            raise

    def get_rfq_status(self, rfq_id: str) -> Dict[str, Any]:
        """Get RFQ status"""
        try:
            if rfq_id not in self.rfqs:
                raise ValueError(f"RFQ {rfq_id} not found")
            
            return asdict(self.rfqs[rfq_id])
            
        except Exception as e:
            logger.error(f"Error getting RFQ status: {e}")
            raise

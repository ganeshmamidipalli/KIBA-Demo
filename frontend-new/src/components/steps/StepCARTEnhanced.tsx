import { motion, AnimatePresence } from "framer-motion";
import { 
  ChevronLeft, 
  ChevronRight, 
  FileText, 
  Send, 
  CheckCircle, 
  Clock, 
  AlertCircle, 
  Download, 
  Mail, 
  Users, 
  Shield, 
  DollarSign, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowRight,
  ExternalLink,
  Eye,
  X,
  Plus,
  Edit,
  Save,
  Loader2
} from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { Badge } from "../ui/badge";
import { Progress } from "../ui/progress";
import { useState, useEffect } from "react";
import type { Vendor } from "../../types";

// Enhanced vendor evaluation types
interface VendorEvaluation {
  vendorName: string;
  productTitle: string;
  price?: { value: number; currency: string; sourceText?: string };
  availability?: { inStock?: boolean; leadTimeDays?: number; sourceText?: string };
  delivery?: { toLocation?: string; promiseDays?: number; terms?: string; sourceText?: string };
  warranty?: string;
  link: string;
  domain: string;
  contact?: { email?: string; phone?: string; formUrl?: string };
  evidence: Array<{ label: string; snippet: string; xpathOrSelector?: string }>;
  lastCheckedAt: string;
  score: number;
  completeness: {
    hasPrice: boolean;
    hasStockOrLead: boolean;
    hasDeliveryToTarget: boolean;
    hasVendorIdentity: boolean;
    overall: "complete" | "partial" | "missing";
    missingFields: Array<"price"|"availability"|"delivery"|"contact">;
  };
  flags: {
    isOfficialOEM?: boolean;
    isDistributor?: boolean;
    isMarketplace?: boolean;
    possibleMismatch?: boolean;
  };
}

interface StepCARTEnhancedProps {
  selectedVendors: Vendor[];
  onNext: (data: any) => void;
  onBack: () => void;
  currentStep: number;
  productName?: string;
  budget?: string;
  quantity?: string;
  projectScope?: string;
  procurementType?: string;
  serviceProgram?: string;
  technicalPOC?: string;
  projectKeys?: string[];
}

export function StepCARTEnhanced({
  selectedVendors,
  onNext,
  onBack,
  currentStep,
  productName = "",
  budget = "0",
  quantity = "1",
  projectScope = "",
  procurementType = "Purchase Order",
  serviceProgram = "Applied Research",
  technicalPOC = "",
  projectKeys = [],
}: StepCARTEnhancedProps) {
  
  // Enhanced state management
  const [evaluatedVendors, setEvaluatedVendors] = useState<VendorEvaluation[]>([]);
  const [selectedPath, setSelectedPath] = useState<'rfq' | 'procurement' | null>(null);
  const [pathRecommendation, setPathRecommendation] = useState<'rfq' | 'procurement' | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [showEvidence, setShowEvidence] = useState<string | null>(null);
  
  // RFQ form state
  const [rfqData, setRfqData] = useState({
    title: `${productName} RFQ`,
    quantity: parseInt(quantity) || 1,
    needBy: '',
    dueDate: '',
    notes: ''
  });
  
  // Procurement form state
  const [procData, setProcData] = useState({
    title: `Procurement Request – ${productName}`,
    department: 'IT',
    budgetCode: 'CAP-2025-NET',
    approver: '',
    needBy: '',
    justification: projectScope,
    type: procurementType,
    serviceProgram: serviceProgram,
    projectsSupported: projectKeys.join(', '),
    estimatedCost: parseFloat(budget) || 0,
    competitionType: 'Competitive',
    multipleVendorsAvailable: selectedVendors.length > 1,
    scopeBrief: projectScope,
    vendorEvaluation: [] as Array<{name: string, contact: string, status: string}>
  });

  // Evaluate vendors on component mount
  useEffect(() => {
    if (selectedVendors.length > 0) {
      evaluateVendors();
    }
  }, [selectedVendors]);

  // Auto-recommend path based on vendor completeness
  useEffect(() => {
    if (evaluatedVendors.length > 0) {
      const hasIncompleteVendors = evaluatedVendors.some(v => v.completeness.overall !== 'complete');
      setPathRecommendation(hasIncompleteVendors ? 'rfq' : 'procurement');
    }
  }, [evaluatedVendors]);

  // Simulate vendor evaluation (replace with actual API call)
  const evaluateVendors = async () => {
    setIsEvaluating(true);
    
    // Simulate evaluation delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const evaluations: VendorEvaluation[] = selectedVendors.map((vendor, index) => {
      // Simulate different completeness scenarios
      const scenarios = [
        { hasPrice: true, hasStock: true, hasDelivery: true, hasContact: true }, // Complete
        { hasPrice: false, hasStock: true, hasDelivery: true, hasContact: true }, // Missing price
        { hasPrice: true, hasStock: false, hasDelivery: true, hasContact: false }, // Missing stock/contact
        { hasPrice: true, hasStock: true, hasDelivery: false, hasContact: true }, // Missing delivery
      ];
      
      const scenario = scenarios[index % scenarios.length];
      
      const missingFields: Array<"price"|"availability"|"delivery"|"contact"> = [];
      if (!scenario.hasPrice) missingFields.push('price');
      if (!scenario.hasStock) missingFields.push('availability');
      if (!scenario.hasDelivery) missingFields.push('delivery');
      if (!scenario.hasContact) missingFields.push('contact');
      
      const overall = missingFields.length === 0 ? 'complete' : 
                     missingFields.length <= 2 ? 'partial' : 'missing';
      
      return {
        vendorName: vendor.vendor_name || vendor.name || `Vendor ${index + 1}`,
        productTitle: vendor.product_name || productName,
        price: scenario.hasPrice ? {
          value: vendor.price || Math.floor(Math.random() * 5000) + 1000,
          currency: 'USD',
          sourceText: 'Found on product page'
        } : undefined,
        availability: scenario.hasStock ? {
          inStock: Math.random() > 0.3,
          leadTimeDays: Math.floor(Math.random() * 30) + 1,
          sourceText: 'Stock status confirmed'
        } : undefined,
        delivery: scenario.hasDelivery ? {
          toLocation: 'Wichita, KS',
          promiseDays: Math.floor(Math.random() * 30) + 1,
          terms: 'Standard shipping',
          sourceText: 'Delivery promise verified'
        } : undefined,
        warranty: '1 year manufacturer warranty',
        link: vendor.purchase_url || vendor.website || '#',
        domain: vendor.vendor_name?.toLowerCase().replace(/\s+/g, '') + '.com' || 'vendor.com',
        contact: scenario.hasContact ? {
          email: `sales@${vendor.vendor_name?.toLowerCase().replace(/\s+/g, '')}.com`,
          phone: '(555) 123-4567'
        } : undefined,
        evidence: [
          { label: 'Price', snippet: scenario.hasPrice ? `$${vendor.price || '1,200'}` : 'Not found' },
          { label: 'Stock', snippet: scenario.hasStock ? 'In stock' : 'Lead time unknown' },
          { label: 'Delivery', snippet: scenario.hasDelivery ? 'Ships to Wichita' : 'Delivery not confirmed' },
          { label: 'Contact', snippet: scenario.hasContact ? 'sales@vendor.com' : 'Contact info missing' }
        ],
        lastCheckedAt: new Date().toISOString(),
        score: Math.floor(Math.random() * 40) + 60, // 60-100
        completeness: {
          hasPrice: scenario.hasPrice,
          hasStockOrLead: scenario.hasStock,
          hasDeliveryToTarget: scenario.hasDelivery,
          hasVendorIdentity: true,
          overall,
          missingFields
        },
        flags: {
          isOfficialOEM: Math.random() > 0.7,
          isDistributor: Math.random() > 0.5,
          isMarketplace: Math.random() > 0.8,
          possibleMismatch: Math.random() > 0.9
        }
      };
    });
    
    setEvaluatedVendors(evaluations);
    setIsEvaluating(false);
  };

  // Generate RFQ email template
  const generateRFQEmail = () => {
    const vendor = evaluatedVendors[0];
    const subject = `RFQ: ${productName} — Qty ${rfqData.quantity} — ${rfqData.needBy}`;
    const body = `Hello ${vendor?.vendorName || 'Vendor'},

We would like a formal quote for:
• Product: ${productName}
• Quantity: ${rfqData.quantity}
• Delivery: to Wichita, KS by ${rfqData.needBy}
• Requirements: ${projectScope}
• Warranty/Support: please specify
• Validity: 30 days preferred

Please include:
• Unit price and extended total (USD)
• Availability or lead time
• Taxes, shipping, and any fees
• Payment terms and return policy
• Point of contact for fulfillment

${rfqData.notes ? `Notes: ${rfqData.notes}` : ''}

Kindly respond by ${rfqData.dueDate}. Thank you!

Best regards,
${technicalPOC || 'Procurement Team'}`;

    return { subject, body };
  };

  // Generate procurement document data
  const generateProcurementDoc = () => {
    return {
      title: procData.title,
      department: procData.department,
      budgetCode: procData.budgetCode,
      approver: procData.approver,
      needBy: procData.needBy,
      justification: procData.justification,
      type: procData.type,
      serviceProgram: procData.serviceProgram,
      projectsSupported: procData.projectsSupported,
      estimatedCost: procData.estimatedCost,
      competitionType: procData.competitionType,
      multipleVendorsAvailable: procData.multipleVendorsAvailable,
      scopeBrief: procData.scopeBrief,
      vendorEvaluation: evaluatedVendors.map(v => ({
        name: v.vendorName,
        contact: v.contact?.email || 'Contact info missing',
        status: v.completeness.overall === 'complete' ? 'Quote available' : 'Quote requested'
      }))
    };
  };

  // Handle form submission
  const handleSubmit = () => {
    if (selectedPath === 'rfq') {
      const rfqEmail = generateRFQEmail();
      onNext({
        type: 'rfq',
        data: {
          ...rfqData,
          email: rfqEmail,
          vendors: evaluatedVendors
        }
      });
    } else if (selectedPath === 'procurement') {
      const procDoc = generateProcurementDoc();
      onNext({
        type: 'procurement',
        data: {
          ...procDoc,
          vendors: evaluatedVendors
        }
      });
    }
  };

  // Validation
  const isRFQValid = rfqData.title.trim() && rfqData.quantity > 0 && rfqData.needBy;
  const isProcValid = procData.title.trim() && procData.department.trim() && 
                     procData.budgetCode.trim() && procData.approver.trim() && procData.needBy;

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/30 p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">CART - Vendor Evaluation & Output</h1>
            <p className="text-muted-foreground">Evaluate selected vendors and choose your output path</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={onBack}>
              <ChevronLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </div>
        </div>

        {/* Vendor Evaluation Section */}
        <Card className="border-blue-500/30 bg-blue-500/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Vendor Evaluation Results
            </CardTitle>
            <CardDescription>
              {isEvaluating ? 'Evaluating vendor information...' : `Evaluated ${evaluatedVendors.length} vendors`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isEvaluating ? (
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Analyzing vendor data and completeness...</span>
              </div>
            ) : (
              <div className="space-y-4">
                {evaluatedVendors.map((vendor, index) => (
                  <Card key={index} className="border shadow-sm">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-3">
                            <h3 className="font-semibold">{vendor.vendorName}</h3>
                            <Badge variant={vendor.completeness.overall === 'complete' ? 'default' : 
                                         vendor.completeness.overall === 'partial' ? 'secondary' : 'destructive'}>
                              {vendor.completeness.overall}
                            </Badge>
                            <Badge variant="outline">Score: {vendor.score}</Badge>
                          </div>
                          
                          {/* Quality indicators */}
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                            <div className="flex items-center gap-2">
                              {vendor.completeness.hasPrice ? (
                                <CheckCircle2 className="h-4 w-4 text-green-500" />
                              ) : (
                                <X className="h-4 w-4 text-red-500" />
                              )}
                              <span className="text-sm">Price</span>
                              {vendor.price && (
                                <span className="text-xs text-muted-foreground">
                                  ${vendor.price.value.toLocaleString()}
                                </span>
                              )}
                            </div>
                            
                            <div className="flex items-center gap-2">
                              {vendor.completeness.hasStockOrLead ? (
                                <CheckCircle2 className="h-4 w-4 text-green-500" />
                              ) : (
                                <X className="h-4 w-4 text-red-500" />
                              )}
                              <span className="text-sm">Availability</span>
                              {vendor.availability && (
                                <span className="text-xs text-muted-foreground">
                                  {vendor.availability.inStock ? 'In stock' : `${vendor.availability.leadTimeDays}d lead`}
                                </span>
                              )}
                            </div>
                            
                            <div className="flex items-center gap-2">
                              {vendor.completeness.hasDeliveryToTarget ? (
                                <CheckCircle2 className="h-4 w-4 text-green-500" />
                              ) : (
                                <X className="h-4 w-4 text-red-500" />
                              )}
                              <span className="text-sm">Delivery</span>
                              {vendor.delivery && (
                                <span className="text-xs text-muted-foreground">
                                  ≤{vendor.delivery.promiseDays}d to {vendor.delivery.toLocation}
                                </span>
                              )}
                            </div>
                            
                            <div className="flex items-center gap-2">
                              {vendor.completeness.hasVendorIdentity ? (
                                <CheckCircle2 className="h-4 w-4 text-green-500" />
                              ) : (
                                <X className="h-4 w-4 text-red-500" />
                              )}
                              <span className="text-sm">Contact</span>
                              {vendor.contact && (
                                <span className="text-xs text-muted-foreground">
                                  {vendor.contact.email}
                                </span>
                              )}
                            </div>
                          </div>
                          
                          {/* Missing fields */}
                          {vendor.completeness.missingFields.length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-3">
                              {vendor.completeness.missingFields.map(field => (
                                <Badge key={field} variant="destructive" className="text-xs">
                                  Missing {field}
                                </Badge>
                              ))}
                            </div>
                          )}
                          
                          {/* Actions */}
                          <div className="flex items-center gap-2">
                            <Button size="sm" variant="outline" onClick={() => setShowEvidence(showEvidence === vendor.vendorName ? null : vendor.vendorName)}>
                              <Eye className="h-4 w-4 mr-1" />
                              View Evidence
                            </Button>
                            <Button size="sm" variant="outline" asChild>
                              <a href={vendor.link} target="_blank" rel="noopener noreferrer">
                                <ExternalLink className="h-4 w-4 mr-1" />
                                Visit Site
                              </a>
                            </Button>
                          </div>
                        </div>
                      </div>
                      
                      {/* Evidence panel */}
                      <AnimatePresence>
                        {showEvidence === vendor.vendorName && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="mt-4 p-3 bg-muted/50 rounded-lg"
                          >
                            <h4 className="font-medium mb-2">Evidence & Sources</h4>
                            <div className="space-y-2">
                              {vendor.evidence.map((item, idx) => (
                                <div key={idx} className="flex justify-between items-center text-sm">
                                  <span className="font-medium">{item.label}:</span>
                                  <span className="text-muted-foreground">{item.snippet}</span>
                                </div>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Path Selection */}
        {!isEvaluating && evaluatedVendors.length > 0 && (
          <Card className="border-green-500/30 bg-green-500/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ArrowRight className="h-5 w-5" />
                Choose Output Path
              </CardTitle>
              <CardDescription>
                {pathRecommendation === 'rfq' 
                  ? 'Some vendors are missing critical information. We recommend generating RFQs to gather complete details.'
                  : 'All vendors have complete information. You can proceed directly to procurement approval.'
                }
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card 
                  className={`cursor-pointer transition-all ${
                    selectedPath === 'rfq' ? 'border-blue-500 bg-blue-500/10' : 'border-border hover:border-blue-300'
                  }`}
                  onClick={() => setSelectedPath('rfq')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3 mb-2">
                      <Send className="h-5 w-5 text-blue-500" />
                      <h3 className="font-semibold">Generate RFQ</h3>
                      {pathRecommendation === 'rfq' && (
                        <Badge variant="default">Recommended</Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Send formal quote requests to vendors for missing information
                    </p>
                  </CardContent>
                </Card>
                
                <Card 
                  className={`cursor-pointer transition-all ${
                    selectedPath === 'procurement' ? 'border-green-500 bg-green-500/10' : 'border-border hover:border-green-300'
                  }`}
                  onClick={() => setSelectedPath('procurement')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3 mb-2">
                      <FileText className="h-5 w-5 text-green-500" />
                      <h3 className="font-semibold">Procurement Document</h3>
                      {pathRecommendation === 'procurement' && (
                        <Badge variant="default">Recommended</Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Create internal procurement approval document
                    </p>
                  </CardContent>
                </Card>
              </div>
            </CardContent>
          </Card>
        )}

        {/* RFQ Form */}
        {selectedPath === 'rfq' && (
          <Card className="border-blue-500/30 bg-blue-500/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Send className="h-5 w-5" />
                RFQ Generation
              </CardTitle>
              <CardDescription>Fill in the details for your RFQ request</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">RFQ Title</label>
                  <Input
                    value={rfqData.title}
                    onChange={(e) => setRfqData({...rfqData, title: e.target.value})}
                    placeholder="Network Switch RFQ"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Quantity</label>
                  <Input
                    type="number"
                    value={rfqData.quantity}
                    onChange={(e) => setRfqData({...rfqData, quantity: parseInt(e.target.value) || 1})}
                    min="1"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Need By</label>
                  <Input
                    type="date"
                    value={rfqData.needBy}
                    onChange={(e) => setRfqData({...rfqData, needBy: e.target.value})}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Due Date for Responses</label>
                  <Input
                    type="date"
                    value={rfqData.dueDate}
                    onChange={(e) => setRfqData({...rfqData, dueDate: e.target.value})}
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium">Additional Notes</label>
                <Textarea
                  value={rfqData.notes}
                  onChange={(e) => setRfqData({...rfqData, notes: e.target.value})}
                  placeholder="Any specific requirements or notes..."
                  rows={3}
                />
              </div>
              
              {/* RFQ Preview */}
              <Card className="border-muted">
                <CardHeader>
                  <CardTitle className="text-sm">RFQ Email Preview</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div><strong>Subject:</strong> {generateRFQEmail().subject}</div>
                    <div><strong>To:</strong> {evaluatedVendors[0]?.contact?.email || 'vendor@example.com'}</div>
                    <div className="mt-2">
                      <strong>Body:</strong>
                      <pre className="mt-1 p-2 bg-muted rounded text-xs whitespace-pre-wrap">
                        {generateRFQEmail().body}
                      </pre>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </CardContent>
          </Card>
        )}

        {/* Procurement Form */}
        {selectedPath === 'procurement' && (
          <Card className="border-green-500/30 bg-green-500/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Procurement Document
              </CardTitle>
              <CardDescription>Fill in the details for your procurement approval</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">Document Title</label>
                  <Input
                    value={procData.title}
                    onChange={(e) => setProcData({...procData, title: e.target.value})}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Department</label>
                  <Input
                    value={procData.department}
                    onChange={(e) => setProcData({...procData, department: e.target.value})}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Budget Code</label>
                  <Input
                    value={procData.budgetCode}
                    onChange={(e) => setProcData({...procData, budgetCode: e.target.value})}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Approver</label>
                  <Input
                    value={procData.approver}
                    onChange={(e) => setProcData({...procData, approver: e.target.value})}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Need By</label>
                  <Input
                    type="date"
                    value={procData.needBy}
                    onChange={(e) => setProcData({...procData, needBy: e.target.value})}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Estimated Cost (USD)</label>
                  <Input
                    type="number"
                    value={procData.estimatedCost}
                    onChange={(e) => setProcData({...procData, estimatedCost: parseFloat(e.target.value) || 0})}
                  />
                </div>
              </div>
              
              <div>
                <label className="text-sm font-medium">Justification</label>
                <Textarea
                  value={procData.justification}
                  onChange={(e) => setProcData({...procData, justification: e.target.value})}
                  placeholder="Explain why this procurement is needed..."
                  rows={3}
                />
              </div>
              
              <div>
                <label className="text-sm font-medium">Scope Brief</label>
                <Textarea
                  value={procData.scopeBrief}
                  onChange={(e) => setProcData({...procData, scopeBrief: e.target.value})}
                  placeholder="Describe the scope and deliverables..."
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>
        )}

        {/* Action Buttons */}
        {selectedPath && (
          <div className="flex items-center justify-between">
            <Button variant="outline" onClick={onBack}>
              <ChevronLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <Button 
              onClick={handleSubmit}
              disabled={
                (selectedPath === 'rfq' && !isRFQValid) ||
                (selectedPath === 'procurement' && !isProcValid)
              }
              className="gap-2"
            >
              {selectedPath === 'rfq' ? (
                <>
                  <Send className="h-4 w-4" />
                  Generate RFQ
                </>
              ) : (
                <>
                  <FileText className="h-4 w-4" />
                  Create Procurement Doc
                </>
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

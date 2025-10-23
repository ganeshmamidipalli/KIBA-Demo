import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  ChevronLeft, 
  ChevronRight, 
  Search, 
  Loader2
} from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { findVendors } from "../../lib/api";
import type { SpecVariant, KPARecommendations } from "../../types";

interface Vendor {
  id: string;
  vendor_name: string;
  product_name: string;
  model: string;
  sku?: string;
  price: number;
  currency: string;
  availability: string;
  ships_to: string[];
  delivery_window_days: number;
  purchase_url: string;
  evidence_urls: string[];
  sales_email: string;
  sales_phone?: string;
  return_policy_url?: string;
  notes?: string;
  us_vendor_verification: {
    is_us_vendor: boolean;
    method: string;
    business_address: string;
  };
  last_checked_utc: string;
  isSelected?: boolean;
  // Additional fields for parsing
  name?: string;
  description?: string;
  website?: string;
  deliveryTime?: string;
  rating?: number;
  contact?: string;
}

interface StepVendorSearchProps {
  productName: string;
  selectedVariants: SpecVariant[];
  searchQuery: string;
  setSearchQuery: (value: string) => void;
  searchOutputText: string;
  setSearchOutputText: (value: string) => void;
  searching: boolean;
  setSearching: (value: boolean) => void;
  kpaRecommendations: KPARecommendations | null;
  onNext: (data?: any) => void;
  onBack: () => void;
}

// Typing animation hook
function useTyping(text: string, speed: number = 18) {
  const [display, setDisplay] = useState("");
  const [done, setDone] = useState(false);
  const timerRef = useRef<number | null>(null);
  
  useEffect(() => {
    setDisplay("");
    setDone(false);
    let i = 0;
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = window.setInterval(() => {
      if (i < text.length) setDisplay((prev) => prev + text[i++]);
      else {
        if (timerRef.current) window.clearInterval(timerRef.current);
        setDone(true);
      }
    }, speed);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [text, speed]);
  
  return { display, done };
}

// Batch type for organizing search results (currently unused but kept for future use)
// interface BatchType {
//   id: number;
//   title: string;
//   items: Vendor[];
//   expanded: boolean;
// }

// Thinking steps for the search process (minimal ChatGPT-style)
const THINKING_STEPS = [
  "Analyzing requirements…",
  "Building search query…", 
  "Searching vendors…",
  "Validating vendor data…",
  "Extracting pricing & availability…",
  "Finalizing results…"
];

export function StepVendorSearch({
  productName,
  selectedVariants,
  searchQuery,
  setSearchQuery,
  searchOutputText,
  setSearchOutputText,
  searching,
  setSearching,
  kpaRecommendations,
  onNext,
  onBack,
}: StepVendorSearchProps) {
  type VendorBatch = { id: number; query: string; userNotes?: string; results: Vendor[]; createdAt: string; hiddenFiltered?: number };
  const [batches, setBatches] = useState<VendorBatch[]>([]);
  const [activeBatchId, setActiveBatchId] = useState<number | null>(null);
  const [selectedVendorsGlobal, setSelectedVendorsGlobal] = useState<Vendor[]>([]);
  const [goodLinkSet, setGoodLinkSet] = useState<Set<string>>(new Set());
  const [queryInput, setQueryInput] = useState<string>("");
  const [notesInput, setNotesInput] = useState<string>("");
  const [autoRan, setAutoRan] = useState<boolean>(false);

  // Enhanced search flow state
  const [searchPhase, setSearchPhase] = useState<'idle' | 'typing' | 'thinking' | 'results'>('idle');
  const [currentThinkingStep, setCurrentThinkingStep] = useState<number>(0);
  const [refineQuery, setRefineQuery] = useState<string>("");
  const [inStockOnly, setInStockOnly] = useState<boolean>(false);
  const [minScore, setMinScore] = useState<number>(80);
  
  // Typing animation for search query
  const { display: typedQuery } = useTyping(searchQuery, 14);
  
  // Abort controller for search requests
  const abortControllerRef = useRef<AbortController | null>(null);

  // Animated dots for thinking indicator
  const [dots, setDots] = useState("");
  useEffect(() => {
    if (searchPhase === 'thinking') {
      const interval = setInterval(() => {
        setDots(prev => prev.length >= 3 ? "" : prev + ".");
      }, 500);
      return () => clearInterval(interval);
    } else {
      setDots("");
    }
  }, [searchPhase]);

  // Minimal thinking steps animation (ChatGPT-style)
  const revealThinkingSteps = async () => {
    setCurrentThinkingStep(0);
    for (let i = 0; i < THINKING_STEPS.length; i++) {
      setCurrentThinkingStep(i);
      await new Promise(resolve => setTimeout(resolve, 600));
    }
  };

  // Enhanced search function with typing animation and thinking steps
  const performEnhancedSearch = async (query: string) => {
    // Start with typing animation
    setSearchPhase('typing');
    
    // Wait for typing animation to complete
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Then show thinking steps
    setSearchPhase('thinking');
    await revealThinkingSteps();
    
    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    const controller = new AbortController();
    abortControllerRef.current = controller;
    
    try {
      setSearching(true);
      const results = await findVendors(query, controller.signal);
      
      if (!controller.signal.aborted) {
        // Filter results based on current filters
        const filteredResults = results.filter((vendor: Vendor) => {
          if (inStockOnly && vendor.availability !== 'In Stock') return false;
          // Add more filtering logic as needed
          return true;
        });
        
        // Create new batch
        const newBatch: VendorBatch = {
          id: Date.now(),
          query,
          results: filteredResults,
          createdAt: new Date().toISOString(),
        };
        
        setBatches(prev => [newBatch, ...prev]);
        setActiveBatchId(newBatch.id);
        setSearchPhase('results');
      }
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        console.error('Search failed:', error);
      }
    } finally {
      setSearching(false);
      abortControllerRef.current = null;
    }
  };

  // Generate enhanced search query based on selected recommendation
  const generateEnhancedSearchQuery = () => {
    if (!kpaRecommendations || selectedVariants.length === 0) {
      return searchQuery; // Fallback to original search query
    }

    // Find the selected recommendation in KPA data
    const selectedVariant = selectedVariants[0]; // Assuming single selection for now
    const selectedRecommendation = kpaRecommendations.recommendations.find(
      rec => rec.id === selectedVariant.id
    );

    if (!selectedRecommendation || !selectedRecommendation.vendor_search) {
      return searchQuery; // Fallback to original search query
    }

    const vendorSearch = selectedRecommendation.vendor_search;
    
    // Build enhanced search query using vendor_search data
    let enhancedQuery = vendorSearch.query_seed || "";
    
    // Replace placeholders with actual values
    enhancedQuery = enhancedQuery
      .replace(/\{MODEL\}/g, vendorSearch.model_name || productName)
      .replace(/\{SPECBITS\}/g, vendorSearch.spec_fragments?.join(" ") || "")
      .replace(/\{REGION\}/g, vendorSearch.region_hint || "")
      .replace(/\{BUDGET\}/g, vendorSearch.budget_hint_usd?.toString() || "");

    // If no query_seed, build one from available data
    if (!enhancedQuery || enhancedQuery === vendorSearch.query_seed) {
      const model = vendorSearch.model_name || productName;
      const specs = vendorSearch.spec_fragments?.join(" ") || "";
      const budget = vendorSearch.budget_hint_usd ? `under $${vendorSearch.budget_hint_usd}` : "";
      const region = vendorSearch.region_hint ? `in ${vendorSearch.region_hint}` : "";
      
      enhancedQuery = `best ${model} ${specs} ${budget} ${region} vendors suppliers distributors`.trim();
    }

    return enhancedQuery;
  };

  // Seed query input from recommendations when available (no auto-run)
  useEffect(() => {
    const enhanced = generateEnhancedSearchQuery();
    if (enhanced && enhanced !== searchQuery) {
      setSearchQuery(enhanced);
      setQueryInput(enhanced);
    }
  }, [selectedVariants, kpaRecommendations, productName]);

  // In-memory only; no persistence across refresh/navigation

  // Reset state when the selected variant changes (new recommendation)
  useEffect(() => {
    const currentId = selectedVariants && selectedVariants.length > 0 ? (selectedVariants[0].id || selectedVariants[0].title) : null;
    const prevId = (window as any).__kiba_prev_variant_id || null;
    if (currentId && prevId && currentId !== prevId) {
      try { sessionStorage.removeItem('vendorSearch.autoRanOnce'); } catch {}
      setBatches([]);
      setActiveBatchId(null);
      setSelectedVendorsGlobal([]);
      setGoodLinkSet(new Set());
      setAutoRan(false);
      setSearchOutputText("");
    }
    (window as any).__kiba_prev_variant_id = currentId;
  }, [selectedVariants]);

  // When raw output changes (after a run), attach to the latest batch results
  useEffect(() => {
    if (!searchOutputText) return;
    if (activeBatchId == null) return;
    const parsedAll = parseVendorsFromOutput(searchOutputText, selectedVariants[0]?.title || productName);
    let parsed = parsedAll;
    // If we have validated links, filter out vendors with bad links
    if (goodLinkSet && goodLinkSet.size > 0) {
      parsed = parsed.filter(v => !v.purchase_url || goodLinkSet.has(v.purchase_url));
    }
    const hidden = Math.max(0, parsedAll.length - parsed.length);
    setBatches(prev => prev.map(b => b.id === activeBatchId ? { ...b, results: parsed, hiddenFiltered: hidden } : b));
  }, [searchOutputText]);

  // Auto-run the very first search only once after arriving from recommendations.
  // If the user navigates away and returns, do NOT auto-run again (guarded via sessionStorage flag).
  useEffect(() => {
    if (autoRan) return;
    if (batches.length > 0) return;
    if (selectedVariants.length === 0) return;
    // Prevent repeated auto-runs across back/forward navigation within the same tab
    if (typeof window !== 'undefined' && sessionStorage.getItem('vendorSearch.autoRanOnce') === '1') return;
    // Prefer seeded queryInput, otherwise fall back to generated searchQuery
    const candidate = (queryInput || searchQuery || '').trim();
    if (!candidate) return;
    setAutoRan(true);
    try { sessionStorage.setItem('vendorSearch.autoRanOnce', '1'); } catch {}
    performVendorSearch(false);
  }, [selectedVariants, batches.length, queryInput, searchQuery]);

  // Removed raw text reveal; only show parsed vendor list

  // Parse vendors from web-search output text into a simple structure
  const parseVendorsFromOutput = (text: string, modelName: string): Vendor[] => {
    const results: Vendor[] = [];
    let id = 1;
    const sections = text.split(/\n\s*\n/).map(s => s.trim()).filter(Boolean);
    const urlRegex = /(https?:\/\/[^\s)]+)\b/g;

    for (const sec of sections) {
      // Try to capture leading bullet vendor name
      const firstLine = sec.split("\n")[0] || "";
      const nameMatch = firstLine
        .replace(/^[-•\d.\s]+/, "")
        .replace(/\s{2,}.*/, "")
        .trim();

      const urls = Array.from(sec.matchAll(urlRegex)).map(m => m[1]);
      if (!nameMatch && urls.length === 0) continue;

      const vendor: Vendor = {
        id: `vendor-${id++}`,
        vendor_name: nameMatch || urls[0] || `Vendor ${id}`,
        product_name: modelName,
        model: modelName,
        price: 0,
        currency: 'USD',
        availability: 'unknown',
        ships_to: ['USA'],
        delivery_window_days: 0,
        purchase_url: urls[0] || '',
        evidence_urls: urls,
        sales_email: '',
        notes: sec.length > 300 ? sec.slice(0, 300) + '…' : sec,
        us_vendor_verification: { is_us_vendor: true, method: 'web_search', business_address: '' },
        last_checked_utc: new Date().toISOString(),
        isSelected: false
      };

      // Filter duplicates by name or URL
      if (!results.some(v => v.vendor_name === vendor.vendor_name || (v.purchase_url && v.purchase_url === vendor.purchase_url))) {
        results.push(vendor);
      }
    }

    // If nothing parsed, return empty
    return results;
  };

  // Handle vendor selection toggle
  const handleVendorSelect = (vendor: Vendor) => {
    const isSelected = selectedVendorsGlobal.some(v => v.id === vendor.id);
    if (isSelected) {
      setSelectedVendorsGlobal(prev => prev.filter(v => v.id !== vendor.id));
    } else {
      setSelectedVendorsGlobal(prev => [...prev, vendor]);
    }
  };
  const [searchStatus, setSearchStatus] = useState("");
  const [maxResults] = useState(10);
  // Removed legacy autoSearching; rely on `searching` only
  const [searchQueryDisplay, setSearchQueryDisplay] = useState("");
  const [isTypingQuery, setIsTypingQuery] = useState(false);
  const [searchSteps, setSearchSteps] = useState<string[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [showSearchSteps, setShowSearchSteps] = useState(false);

  // Type out text with animation
  const typeText = (text: string, callback?: () => void) => {
    setIsTypingQuery(true);
    setSearchQueryDisplay("");
    let index = 0;
    
    const typeInterval = setInterval(() => {
      if (index < text.length) {
        setSearchQueryDisplay(text.substring(0, index + 1));
        index++;
      } else {
        clearInterval(typeInterval);
        setIsTypingQuery(false);
        if (callback) callback();
      }
    }, 50); // 50ms delay between characters
  };

  // Show search steps with animation
  const startSearchSteps = () => {
    const steps = [
      "🔍 Analyzing product requirements...",
      "📝 Building optimized search query...",
      "🌐 Searching US vendors...",
      "✅ Validating vendor data...",
      "📊 Extracting pricing and availability...",
      "🎯 Finalizing vendor results..."
    ];
    
    setSearchSteps(steps);
    setCurrentStep(0);
    setShowSearchSteps(true);
    
    const stepInterval = setInterval(() => {
      setCurrentStep(prev => {
        if (prev < steps.length - 1) {
          return prev + 1;
        } else {
          clearInterval(stepInterval);
          return prev;
        }
      });
    }, 2000); // 2 seconds per step
  };

  // Removed unused buildSearchQueryLocal helper

  const performVendorSearch = async (withNotes: boolean = false) => {
    if (selectedVariants.length === 0) return;
    const baseQuery = (queryInput || searchQuery || '').trim();
    if (!baseQuery) return;

    const selectedVariant = selectedVariants[0];
    const combinedQuery = withNotes && notesInput.trim()
      ? `${baseQuery}. Consider: ${notesInput.trim()}`
      : baseQuery;

    // Start with typing animation
    setSearchPhase('typing');
    setSearching(true);
    setSearchStatus("Finding vendors...");

    // Wait for typing animation to complete
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Then show thinking steps
    setSearchPhase('thinking');
    await revealThinkingSteps();

    // Create a new batch entry first and set active
    const newBatchId = (batches[batches.length - 1]?.id || 0) + 1;
    const newBatch: VendorBatch = { id: newBatchId, query: combinedQuery, userNotes: withNotes ? notesInput.trim() : undefined, results: [], createdAt: new Date().toISOString() };
    setBatches(prev => [...prev, newBatch]);
    setActiveBatchId(newBatchId);

    try {
      // Animate query typing + steps for UX
      typeText(combinedQuery, () => {
        setTimeout(() => {
          startSearchSteps();
          setTimeout(async () => {
            try {
              const vendorData = await findVendors(
                selectedVariant,
                kpaRecommendations,
                0,
                maxResults,
                false,
                combinedQuery
              );
              setSearchStatus("Vendor search complete!");
              const output = vendorData.output_text || `Found ${vendorData.results?.length || 0} vendors for ${selectedVariant.title}`;
              setSearchOutputText(output);
              setSearchPhase('results');
              // Capture validated links if provided by backend
              try {
                const links = (vendorData.validated_links || []) as Array<{url: string, status: number|null}>;
                const ok = new Set<string>();
                for (const l of links) {
                  if (l && typeof l.url === 'string' && l.url && typeof l.status === 'number' && l.status >= 200 && l.status < 400) {
                    ok.add(l.url);
                  }
                }
                if (ok.size > 0) setGoodLinkSet(ok);
              } catch {}
              // results parsing handled by useEffect on searchOutputText
            } catch (error: any) {
              console.error('Error finding vendors:', error);
              setSearchStatus(`❌ Vendor Search Error: ${error.message}`);
            } finally {
              setSearching(false);
              setSearchStatus("");
            }
          }, 12000);
        }, 2000);
      });
    } catch (error: any) {
      console.error('Error finding vendors:', error);
      setSearchStatus(`❌ Vendor Search Error: ${error.message}`);
      setSearching(false);
      setSearchStatus("");
    }
  };

  // No auto search. Seed query only.

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="mx-auto max-w-4xl space-y-4 px-4"
    >
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
          Vendor Search
        </h2>
        <p className="text-muted-foreground text-sm">Search US vendors, compare batches, and add picks to RFQ</p>
      </div>

      {selectedVariants.length === 0 ? (
        <Card className="border-yellow-500/30 bg-yellow-500/5">
          <CardContent className="pt-12 pb-12 text-center">
            <h3 className="text-lg font-semibold mb-2">No Variant Selected</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Please go back and select a recommendation variant first.
            </p>
            <Button onClick={onBack} variant="outline">
              Back to Recommendations
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Enhanced Search Flow */}
          {(searchPhase === 'typing' || searchPhase === 'thinking' || (typedQuery && searchPhase !== 'idle')) && (
            <Card className="border shadow-sm">
              <CardContent className="py-4 space-y-3">
                <div className="font-mono text-sm leading-6">
                  <span className="opacity-70">Assistant query:</span>
                  <div className="mt-1 rounded-xl bg-muted px-3 py-2 whitespace-pre-wrap">
                    {typedQuery}
                    <span className="inline-block w-2 h-4 translate-y-0.5 ml-1 bg-foreground animate-pulse" />
                  </div>
                </div>
                <AnimatePresence>
                  {searchPhase === 'thinking' && (
                    <motion.div 
                      initial={{ opacity: 0, y: 10 }} 
                      animate={{ opacity: 1, y: 0 }} 
                      exit={{ opacity: 0, y: -10 }}
                      className="flex items-center gap-3 text-sm text-muted-foreground bg-muted/30 rounded-lg px-4 py-3"
                      role="status"
                      aria-live="polite"
                    >
                      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                      <span>
                        {THINKING_STEPS[currentThinkingStep] || THINKING_STEPS[THINKING_STEPS.length - 1]}
                        <span className="inline-block w-2 ml-1">{dots}</span>
                      </span>
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
            </Card>
          )}

          {/* Filters (only after results) */}
          {searchPhase === 'results' && (
            <Card className="border shadow-sm">
              <CardContent className="py-3">
                <div className="flex flex-col md:flex-row items-center gap-3 text-sm">
                  <label className="inline-flex items-center gap-2">
                    <input 
                      type="checkbox" 
                      className="accent-current" 
                      checked={inStockOnly} 
                      onChange={(e) => setInStockOnly(e.target.checked)} 
                    />
                    In-stock only
                  </label>
                  <div className="flex items-center gap-2">
                    <span>Min score</span>
                    <Input 
                      type="number" 
                      min={0} 
                      max={100} 
                      value={minScore} 
                      onChange={(e) => setMinScore(Number(e.target.value) || 0)} 
                      className="w-20" 
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Selected Variant Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                {searching ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                    Searching vendors...
                  </>
                ) : (
                  "Searching for:"
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-lg text-primary">{selectedVariants[0].title}</h3>
                  <p className="text-sm text-muted-foreground mt-1">{selectedVariants[0].summary}</p>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-2xl font-bold text-primary">
                      ${selectedVariants[0].est_unit_price_usd.toLocaleString()}
                    </p>
                    <p className="text-xs text-muted-foreground">per unit • qty: {selectedVariants[0].quantity}</p>
                  </div>
                  <Button 
                    onClick={() => {
                      performEnhancedSearch(generateEnhancedSearchQuery());
                    }}
                    disabled={searching}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    <Search className="h-4 w-4 mr-2" />
                    Continue Vendor Search
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Search Query Display */}
          {searchQueryDisplay && (
            <Card className="border-green-500/30 bg-green-500/5">
            <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Search className="h-4 w-4 text-green-600" />
                  Generated Search Query
                  {isTypingQuery && <Loader2 className="h-4 w-4 animate-spin text-green-600" />}
                </CardTitle>
            </CardHeader>
              <CardContent>
                <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm">
                  <span className="text-green-600">{searchQueryDisplay}</span>
                  {isTypingQuery && <span className="animate-pulse">|</span>}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Search Steps */}
          {showSearchSteps && searchSteps.length > 0 && (
            <Card className="border-blue-500/30 bg-blue-500/5">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                  Search Process
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {searchSteps.map((step, index) => (
                    <div
                      key={index}
                      className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
                        index <= currentStep
                          ? "bg-blue-100 text-blue-800 border border-blue-200"
                          : "bg-gray-50 text-gray-500"
                      }`}
                    >
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        index < currentStep
                          ? "bg-green-500 text-white"
                          : index === currentStep
                          ? "bg-blue-500 text-white animate-pulse"
                          : "bg-gray-300 text-gray-600"
                      }`}>
                        {index < currentStep ? "✓" : index + 1}
                      </div>
                      <span className="text-sm">{step}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Auto Search Status */}
          {searching && !searchQueryDisplay && (
            <Card className="border-blue-500/30 bg-blue-500/5">
              <CardContent className="pt-6 pb-6 text-center">
                <div className="flex items-center justify-center gap-3">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                  <div>
                    <h3 className="text-lg font-semibold">
                      Searching for vendors...
                    </h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Finding the best vendors for {selectedVariants[0].title}
                    </p>
                    {searching && searchStatus && (
                      <p className="text-xs text-muted-foreground mt-2">{searchStatus}</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Search Controls - simplified */}
          {batches.length === 0 ? (
            <Card className="border-border bg-background/60 backdrop-blur supports-[backdrop-filter]:bg-background/60">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Search className="h-4 w-4" /> Search Vendors
                </CardTitle>
                <CardDescription>Enter a query to start your first search</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <input
                  className="w-full border rounded px-3 py-2 text-sm bg-background text-foreground"
                  placeholder="Search query"
                  value={queryInput}
                  onChange={e => setQueryInput(e.target.value)}
                />
                <div className="flex gap-2">
                  <Button 
                    onClick={() => {
                      performEnhancedSearch(queryInput || searchQuery);
                    }} 
                    disabled={searching || !queryInput.trim()} 
                    className="gap-2"
                  >
                    <Search className="h-4 w-4" /> Run Enhanced Search
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : searchPhase === 'results' && batches.length > 0 ? (
            <Card className="border-border bg-background/60 backdrop-blur supports-[backdrop-filter]:bg-background/60">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Search className="h-4 w-4" /> Refine Search
                </CardTitle>
                <CardDescription>Not satisfied? Add your thoughts and search again (new batch)</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <input
                  className="w-full border rounded px-3 py-2 text-sm bg-background text-foreground"
                  placeholder="Add your thoughts for the next search"
                  value={notesInput}
                  onChange={e => setNotesInput(e.target.value)}
                />
                <div className="flex gap-2">
                  <Button onClick={() => { performVendorSearch(true); setNotesInput(""); }} disabled={searching || !queryInput.trim()} className="gap-2" variant="outline">
                    <Search className="h-4 w-4" /> Search Again with Thoughts
                  </Button>
                </div>
                <p className="text-xs text-gray-500">We'll combine your thoughts with your last query and show a typing animation while searching.</p>
              </CardContent>
            </Card>
          ) : null}

          {/* Batches Sidebar + Active Batch Results */}
          {batches.length > 0 && (
            <Card className="border-primary/20 bg-background/60">
              <CardHeader>
                <CardTitle className="text-base">Vendors Found (Batches)</CardTitle>
                <CardDescription>Click to select vendors to add to CART. Switch batches to compare.</CardDescription>
                {(() => {
                  const active = batches.find(b => b.id === activeBatchId);
                  return active && active.hiddenFiltered && active.hiddenFiltered > 0 ? (
                    <div className="mt-1 text-xs text-muted-foreground">
                      Filtered {active.hiddenFiltered} vendor{active.hiddenFiltered>1?'s':''} with invalid links
                    </div>
                  ) : null;
                })()}
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="md:col-span-1 border rounded p-2 space-y-2 bg-muted/40">
                    {batches.map(b => {
                      const selectedCount = selectedVendorsGlobal.filter(v =>
                        (b.results || []).some(r => r.id === v.id)
                      ).length;
                      return (
                      <button
                        key={b.id}
                        onClick={() => setActiveBatchId(b.id)}
                        className={`w-full text-left px-3 py-2 rounded border transition-colors ${activeBatchId===b.id? 'bg-primary/10 border-primary':'bg-background border-border hover:bg-muted/50'}`}
                      >
                        <div className="text-sm font-medium">Batch {batches.indexOf(b) + 1}</div>
                        <div className="text-xs text-gray-600 truncate">{b.query}</div>
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>{new Date(b.createdAt).toLocaleTimeString()}</span>
                          {selectedCount > 0 && (
                            <span className="ml-2 inline-block px-2 py-0.5 rounded bg-green-100 text-green-700">{selectedCount} selected</span>
                          )}
                        </div>
                      </button>
                      );
                    })}
                  </div>
                  <div className="md:col-span-3 space-y-3">
                    {/* Per-batch actions */}
                    {activeBatchId && (
                      <div className="flex justify-end">
                        <Button
                          variant="outline"
                          onClick={() => {
                            const activeResults = batches.find(b=>b.id===activeBatchId)?.results || [];
                            const activeIds = new Set(activeResults.map(r=>r.id));
                            setSelectedVendorsGlobal(prev => prev.filter(v => !activeIds.has(v.id)));
                          }}
                        >
                          Clear Selections for This Batch
                        </Button>
                      </div>
                    )}
                    {(batches.find(b=>b.id===activeBatchId)?.results || []).map((v, idx) => {
                      const selected = selectedVendorsGlobal.some(s => s.id === v.id);
                    return (
                      <div key={v.id} className="flex items-start gap-3">
                        <div className="shrink-0 w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center text-primary text-xs">{idx+1}</div>
                        <div className={`flex-1 pr-4 p-3 rounded-2xl border ${selected ? 'border-green-500 bg-green-50 dark:bg-green-950/30' : 'border-border bg-background'}`}>
                          <div className="font-semibold">{idx + 1}. {v.vendor_name}</div>
                          {v.purchase_url && (
                            <a href={v.purchase_url} target="_blank" rel="noreferrer" className="text-blue-600 underline text-sm break-all">
                              {v.purchase_url}
                            </a>
                          )}
                          {v.notes && (
                            <div className="text-xs text-muted-foreground mt-1 whitespace-pre-wrap">{v.notes}</div>
                          )}
                        </div>
                        <div className="self-center">
                          <Button variant={selected ? 'secondary' : 'outline'} onClick={() => handleVendorSelect(v)}>
                            {selected ? 'Remove' : 'Select'}
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Refine Search Section - Only show after first search results */}
          {searchPhase === 'results' && batches.length > 0 && (
            <Card className="border shadow-sm">
              <CardContent className="py-4 space-y-3">
                <form 
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (refineQuery.trim()) {
                      setSearchPhase('typing');
                      // Create a new batch with refined query
                      const refinedQuery = `${queryInput || searchQuery}\n+ ${refineQuery.trim()}`;
                      performEnhancedSearch(refinedQuery);
                      setRefineQuery("");
                    }
                  }} 
                  className="flex flex-col sm:flex-row items-stretch gap-3"
                >
                  <Input
                    placeholder="Add your thoughts for the next search"
                    value={refineQuery}
                    onChange={(e) => setRefineQuery(e.target.value)}
                  />
                  <Button type="submit" disabled={!refineQuery.trim() || searching}>
                    <Search className="h-4 w-4 mr-2" />
                    Search Again with Thoughts
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}

          {/* Selected CART preview */}
          {selectedVendorsGlobal.length > 0 && (
            <Card className="border-green-500/30 bg-green-500/5">
              <CardHeader>
                <CardTitle className="text-base">CART Preview ({selectedVendorsGlobal.length})</CardTitle>
                <CardDescription>Vendors selected will move to CART in next step</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex justify-end mb-2">
                  <Button variant="outline" onClick={() => setSelectedVendorsGlobal([])}>Clear All Selections</Button>
                </div>
                <ul className="list-decimal ml-6 space-y-1 text-sm">
                  {selectedVendorsGlobal.map(v => (
                    <li key={v.id} className="truncate">
                      {v.vendor_name} {v.purchase_url && (<span className="text-gray-500">- {v.purchase_url}</span>)}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Raw output removed per request */}

          {/* Vendor tiles removed per request */}


          {/* Navigation */}
          <div className="flex justify-between sticky bottom-2 bg-background/70 backdrop-blur rounded-xl px-3 py-2 border">
            <Button onClick={onBack} variant="outline" className="gap-2">
              <ChevronLeft className="h-4 w-4" />
              Back
            </Button>
            <Button
              onClick={() => {
                console.log("StepVendorSearch: Continue button clicked");
                onNext({
                  rawOutput: searchOutputText,
                  generatedQuery: searchQuery,
                  selectedVendors: selectedVendorsGlobal,
                });
              }}
              disabled={selectedVendorsGlobal.length === 0}
              className="gap-2"
            >
              Add to RFQ
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </>
      )}
    </motion.div>
  );
}

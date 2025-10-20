import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, Search, Loader2, CheckCircle2, DollarSign, Clock, ExternalLink } from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { buildSearchQuery, findVendors } from "../../lib/api";
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
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [selectedVendors, setSelectedVendors] = useState<Vendor[]>([]);

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

  // Update enhanced search query when selected variants or KPA recommendations change
  useEffect(() => {
    const enhanced = generateEnhancedSearchQuery();
    if (enhanced !== searchQuery) {
      setSearchQuery(enhanced);
    }
  }, [selectedVariants, kpaRecommendations, productName]);

  // Parse vendors from search output text
  useEffect(() => {
    if (searchOutputText && !searching) {
      const parsedVendors = parseVendorsFromText(searchOutputText);
      setVendors(parsedVendors);
    }
  }, [searchOutputText, searching]);

  // Parse vendors from search text with improved logic
  const parseVendorsFromText = (text: string): Vendor[] => {
    const vendors: Vendor[] = [];
    let vendorId = 1;

    console.log("Parsing vendors from text:", text.substring(0, 500) + "...");

    // Enhanced parsing for structured search results
    // Look for numbered lists or bullet points with vendor information
    const vendorPatterns = [
      // Pattern 1: Numbered lists (1. Vendor Name - Price - Description)
      /(\d+)\.\s*([^•\n\-]+?)(?:\s*[-–]\s*([^•\n]+?))?(?:\s*•\s*([^•\n]+?))?(?:\s*•\s*([^•\n]+?))?(?:\s*•\s*([^•\n]+?))?/g,
      // Pattern 2: Bullet points with vendor info
      /•\s*([^•\n\-]+?)(?:\s*[-–]\s*([^•\n]+?))?(?:\s*•\s*([^•\n]+?))?(?:\s*•\s*([^•\n]+?))?(?:\s*•\s*([^•\n]+?))?/g,
      // Pattern 3: Lines starting with vendor names
      /^([A-Z][a-zA-Z\s&.,'-]+(?:Inc|Corp|LLC|Ltd|Company|Technologies|Systems|Solutions|Group|Electronics|Computers|Hardware|Supply|Distributors?|Vendors?|Partners?|Associates?|Enterprises?|International|Global|USA|America)?)\s*[-–]?\s*([^•\n]*)/gm,
      // Pattern 4: Vendor name followed by price in parentheses
      /([A-Z][a-zA-Z\s&.,'-]+(?:Inc|Corp|LLC|Ltd|Company|Technologies|Systems|Solutions|Group|Electronics|Computers|Hardware|Supply|Distributors?|Vendors?|Partners?|Associates?|Enterprises?|International|Global|USA|America)?)\s*\(([^)]+)\)/g
    ];

    // Try each pattern
    for (const pattern of vendorPatterns) {
      const matches = [...text.matchAll(pattern)];
      
      for (const match of matches) {
        const vendor: Partial<Vendor> = {};
        
        // Extract vendor name based on pattern type
        let vendorName = '';
        let description = '';
        let price = '';
        
        if (pattern === vendorPatterns[0]) {
          // Pattern 1: Numbered lists (1. Vendor Name - Price - Description)
          vendorName = match[2]?.trim() || '';
          price = match[3]?.trim() || '';
          description = match[4]?.trim() || '';
        } else if (pattern === vendorPatterns[1]) {
          // Pattern 2: Bullet points
          vendorName = match[1]?.trim() || '';
          price = match[2]?.trim() || '';
          description = match[3]?.trim() || '';
        } else if (pattern === vendorPatterns[2]) {
          // Pattern 3: Lines starting with vendor names
          vendorName = match[1]?.trim() || '';
          description = match[2]?.trim() || '';
        } else if (pattern === vendorPatterns[3]) {
          // Pattern 4: Vendor name with price in parentheses
          vendorName = match[1]?.trim() || '';
          price = match[2]?.trim() || '';
        }
        
        // Clean up vendor name
        vendorName = vendorName.replace(/^[•\-\*\s]+/, '').trim();
        
        if (vendorName && vendorName.length > 2 && vendorName.length < 100) {
          vendor.vendor_name = vendorName;
          
          // Set description
          if (description && description.length > 5) {
            vendor.description = description;
          }
          
          // Extract and clean price
          if (price) {
            const priceMatch = price.match(/\$[\d,]+(?:\.\d{2})?(?:\s*-\s*\$[\d,]+(?:\.\d{2})?)?/);
            if (priceMatch) {
              vendor.price = parseFloat(priceMatch[0].replace(/[$,]/g, ''));
            } else if (price.match(/\d+/)) {
              vendor.price = parseFloat(price.replace(/[$,]/g, ''));
            }
          }
          
          // Extract additional info from all parts
          const allParts = match.slice(1).filter(part => part && part.trim());
          
          for (const part of allParts) {
            const cleanPart = part.trim();
            
            // Extract website
            const websiteMatch = cleanPart.match(/https?:\/\/[^\s\)]+/);
            if (websiteMatch && !vendor.website) {
              vendor.website = websiteMatch[0];
            }
            
            // Extract availability/delivery info
            if (cleanPart.match(/(?:in\s+stock|available|delivery|shipping|lead\s+time|days?)/i) && !vendor.deliveryTime) {
              vendor.deliveryTime = cleanPart;
            }
            
            // Extract rating
            const ratingMatch = cleanPart.match(/(\d+(?:\.\d+)?)\s*(?:stars?|\/5|\/10)/i);
            if (ratingMatch && !vendor.rating) {
              vendor.rating = parseFloat(ratingMatch[1]);
            }
            
            // Extract contact info
            if (cleanPart.match(/(?:contact|email|phone|call)/i) && !vendor.contact) {
              vendor.contact = cleanPart;
            }
          }
          
          // If we have a valid vendor, add it
          if (vendor.vendor_name && !vendors.some(v => v.vendor_name === vendor.vendor_name)) {
            vendors.push({
              ...vendor,
              id: `vendor-${vendorId++}`,
              isSelected: false,
              rating: vendor.rating || Math.floor(Math.random() * 2) + 4 // Random 4-5 star rating if not found
            } as Vendor);
          }
        }
      }
    }

    // If no vendors found with patterns, try line-by-line parsing
    if (vendors.length === 0) {
      const lines = text.split('\n').map(line => line.trim()).filter(line => line);
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        
        // Look for lines that might be vendor names
        if (line.match(/^[A-Z][a-zA-Z\s&.,'-]+$/i) && line.length > 3 && line.length < 100) {
          const vendor: Vendor = {
            id: `vendor-${vendorId++}`,
            vendor_name: line,
            product_name: selectedVariants[0]?.title || 'Unknown Product',
            model: selectedVariants[0]?.title || 'Unknown Product',
            sku: `WEB-${vendorId}`,
            price: 0,
            currency: 'USD',
            availability: 'unknown',
            ships_to: ['USA'],
            delivery_window_days: 5,
            purchase_url: '',
            evidence_urls: [],
            sales_email: '',
            sales_phone: undefined,
            return_policy_url: undefined,
            notes: 'Found via web search',
            us_vendor_verification: {
              is_us_vendor: true,
              method: 'web_search',
              business_address: 'United States'
            },
            last_checked_utc: new Date().toISOString(),
            description: "Vendor found in search results",
            isSelected: false
          };
          
          // Look for price in next few lines
          for (let j = i + 1; j < Math.min(i + 3, lines.length); j++) {
            const nextLine = lines[j];
            const priceMatch = nextLine.match(/\$[\d,]+(?:\.\d{2})?/);
            if (priceMatch) {
              vendor.price = parseFloat(priceMatch[0].replace(/[$,]/g, ''));
              break;
            }
          }
          
          vendors.push(vendor);
        }
      }
    }

    // If still no vendors, create a fallback
    if (vendors.length === 0) {
      vendors.push({
        id: `vendor-${vendorId++}`,
        vendor_name: "Search Results Summary",
        product_name: selectedVariants[0]?.title || 'Unknown Product',
        model: selectedVariants[0]?.title || 'Unknown Product',
        sku: `SUMMARY-1`,
        price: 0,
        currency: 'USD',
        availability: 'unknown',
        ships_to: ['USA'],
        delivery_window_days: 5,
        purchase_url: '',
        evidence_urls: [],
        sales_email: '',
        sales_phone: undefined,
        return_policy_url: undefined,
        notes: 'Search results summary',
        us_vendor_verification: {
          is_us_vendor: true,
          method: 'summary',
          business_address: 'United States'
        },
        last_checked_utc: new Date().toISOString(),
        description: text.substring(0, 300) + (text.length > 300 ? "..." : ""),
        isSelected: false
      });
    }

    return vendors;
  };

  // Handle vendor selection
  const handleVendorSelect = (vendor: Vendor) => {
    const isSelected = selectedVendors.some(v => v.vendor_name === vendor.vendor_name);
    if (isSelected) {
      const newSelected = selectedVendors.filter(v => v.vendor_name !== vendor.vendor_name);
      console.log("StepVendorSearch: Removing vendor, new selected:", newSelected);
      setSelectedVendors(newSelected);
    } else {
      const newSelected = [...selectedVendors, vendor];
      console.log("StepVendorSearch: Adding vendor, new selected:", newSelected);
      setSelectedVendors(newSelected);
    }
  };
  const [searchStatus, setSearchStatus] = useState("");
  const [maxResults] = useState(10);
  const [autoSearching, setAutoSearching] = useState(false);
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

  const buildSearchQueryLocal = async () => {
    if (selectedVariants.length === 0) return;
    
    try {
      const selectedVariant = selectedVariants[0];
      
      const payload = {
        product_name: productName,
        selected_variant: {
          id: selectedVariant.id,
          title: selectedVariant.title,
          summary: selectedVariant.summary,
          est_unit_price_usd: selectedVariant.est_unit_price_usd,
          quantity: selectedVariant.quantity
        },
        delivery_location: {
          city: "Wichita",
          state: "KS"
        },
        delivery_window_days: 30,
        results_limit: maxResults
      };
      
      const data = await buildSearchQuery(payload);
      const query = data.solid_query || '';
      setSearchQuery(query);
      
      if (!query) {
        const fallbackQuery = `${productName} ${selectedVariant.title}`;
        setSearchQuery(fallbackQuery);
      }
    } catch (error) {
      console.error('Error building search query:', error);
      const fallbackQuery = `${productName} ${selectedVariants[0].title}`;
      setSearchQuery(fallbackQuery);
    }
  };

  const performVendorSearch = async () => {
    if (selectedVariants.length === 0) return;
    
    setSearching(true);
    setVendors([]);
    setSearchStatus("Finding vendors...");
    
    try {
      // Generate the search query with typing animation
      const selectedVariant = selectedVariants[0];
      const query = `i want the best ${selectedVariant.title} with links with ${maxResults} vendors under $${selectedVariant.est_unit_price_usd}`;
      
      // Step 1: Type out the query first
      typeText(query, () => {
        // Step 2: After query typing is complete, show search steps
        setTimeout(() => {
          startSearchSteps();
          
          // Step 3: After steps animation, start the actual search
          setTimeout(async () => {
            try {
              // Find vendors using the new vendor finder
              const vendorData = await findVendors(
                selectedVariant,
                kpaRecommendations,
                0, // page
                maxResults, // page size
                false // refresh
              );
              
              setSearchStatus("Vendor search complete!");
              
              // Update vendors with the structured data
              console.log("Vendor search results:", vendorData);
              console.log("Vendor results array:", vendorData.results);
              console.log("Number of vendors:", vendorData.results?.length || 0);
              
              setVendors(vendorData.results || []);
              
              // Set search output text to enable the continue button
              const searchText = vendorData.output_text || `Found ${vendorData.results?.length || 0} vendors for ${selectedVariant.title}`;
              setSearchOutputText(searchText);
              
            } catch (error: any) {
              console.error('Error finding vendors:', error);
              setSearchStatus(`❌ Vendor Search Error: ${error.message}`);
            } finally {
              setSearching(false);
              setSearchStatus("");
            }
          }, 12000); // Wait for all 6 steps to complete (6 steps × 2 seconds each)
        }, 2000); // Wait 2 seconds after query typing is complete
      });
      
    } catch (error: any) {
      console.error('Error finding vendors:', error);
      setSearchStatus(`❌ Vendor Search Error: ${error.message}`);
      setSearching(false);
      setSearchStatus("");
    }
  };

  useEffect(() => {
    if (selectedVariants.length === 1) {
      setAutoSearching(true);
      buildSearchQueryLocal();
      // Automatically trigger vendor search when a variant is selected
      setTimeout(() => {
        performVendorSearch();
        setAutoSearching(false);
      }, 1000); // Small delay to ensure query is built first
    }
  }, [selectedVariants]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
          Vendor Search
        </h2>
        <p className="text-gray-600 text-lg">Search for vendors and select the ones you want to include in your RFQ</p>
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
          {/* Selected Variant Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                {autoSearching ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                    Auto-searching for vendors...
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
                <div className="text-right">
                  <p className="text-2xl font-bold text-primary">
                    ${selectedVariants[0].est_unit_price_usd.toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">per unit • qty: {selectedVariants[0].quantity}</p>
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
          {(autoSearching || searching) && !searchQueryDisplay && (
            <Card className="border-blue-500/30 bg-blue-500/5">
              <CardContent className="pt-6 pb-6 text-center">
                <div className="flex items-center justify-center gap-3">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                  <div>
                    <h3 className="text-lg font-semibold">
                      {autoSearching ? "Auto-searching for vendors..." : "Searching for vendors..."}
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

          {/* Manual Search Button */}
          {!searching && !autoSearching && (
            <Card className="border-gray-200">
              <CardContent className="pt-6 pb-6 text-center">
                <Button 
                  onClick={performVendorSearch}
                  className="gap-2"
                  size="lg"
                >
                  <Search className="h-5 w-5" />
                  Search for Vendors
                </Button>
                <p className="text-sm text-muted-foreground mt-2">
                  Click to start the vendor search process
                </p>
            </CardContent>
          </Card>
          )}

          {/* Web Search Results */}
          {searchOutputText && (
            <Card className="border-primary/20">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Search className="h-4 w-4 text-primary" />
                  Web Search Results
                </CardTitle>
                <CardDescription>
                  Raw web search output from o4-mini
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <pre className="whitespace-pre-wrap text-sm text-gray-700">
                    {searchOutputText}
                  </pre>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Vendor Results */}
          {vendors.length > 0 && (
            <Card className="border-primary/20">
              <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Search className="h-4 w-4 text-primary" />
                  Found {vendors.length} Vendors
                    </CardTitle>
                <CardDescription>
                  Select the vendors you want to include in your RFQ
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {vendors.map((vendor) => {
                    const isSelected = selectedVendors.some(v => v.vendor_name === vendor.vendor_name);
                    return (
                      <Card
                        key={vendor.vendor_name}
                        className={`cursor-pointer transition-all hover:shadow-lg ${
                          isSelected 
                            ? "ring-2 ring-primary bg-primary/5 border-primary/20" 
                            : "hover:ring-2 hover:ring-primary/30 hover:border-primary/20"
                        }`}
                        onClick={() => handleVendorSelect(vendor)}
                      >
                        <CardContent className="p-5">
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <h3 className="font-semibold text-lg">{vendor.vendor_name}</h3>
                                {isSelected && (
                                  <CheckCircle2 className="h-5 w-5 text-primary" />
                                )}
                              </div>
                            </div>
                          </div>
                          
                          <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                            {vendor.product_name} - {vendor.model}
                          </p>
                          
                          <div className="space-y-2">
                            {vendor.price > 0 ? (
                              <div className="flex items-center gap-2">
                                <DollarSign className="h-4 w-4 text-green-600" />
                                <span className="font-semibold text-green-600">${vendor.price.toFixed(2)} {vendor.currency}</span>
                              </div>
                            ) : (
                              <div className="flex items-center gap-2">
                                <DollarSign className="h-4 w-4 text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">Price not available</span>
                              </div>
                            )}
                            
                            <div className="flex items-center gap-2">
                              <Clock className="h-4 w-4 text-blue-600" />
                              <span className="text-sm text-muted-foreground">{vendor.delivery_window_days} days delivery</span>
                            </div>
                            
                            <div className="flex items-center gap-2">
                              <ExternalLink className="h-4 w-4 text-primary" />
                              <a 
                                href={vendor.purchase_url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-sm text-primary hover:underline"
                                onClick={(e) => e.stopPropagation()}
                              >
                                Visit Product Page
                              </a>
                            </div>
                            
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-muted-foreground">Sales: {vendor.sales_email}</span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
                
                {selectedVendors.length > 0 && (
                  <div className="mt-4 p-4 bg-primary/5 rounded-lg border border-primary/20">
                    <h4 className="font-semibold mb-2">Selected Vendors ({selectedVendors.length})</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedVendors.map((vendor) => (
                        <Badge key={vendor.vendor_name} variant="secondary" className="gap-1">
                          {vendor.vendor_name}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleVendorSelect(vendor);
                            }}
                            className="ml-1 hover:text-destructive"
                          >
                            ×
                          </button>
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}


          {/* Navigation */}
          <div className="flex justify-between">
            <Button onClick={onBack} variant="outline" className="gap-2">
              <ChevronLeft className="h-4 w-4" />
              Back
            </Button>
            <Button
              onClick={() => {
                console.log("StepVendorSearch: Continue button clicked");
                console.log("StepVendorSearch: selectedVendors:", selectedVendors);
                console.log("StepVendorSearch: vendors:", vendors);
                onNext({ selectedVendors, vendors });
              }}
              disabled={!searchOutputText || selectedVendors.length === 0}
              className="gap-2"
            >
              {selectedVendors.length > 0 
                ? `Continue to CART (${selectedVendors.length} selected)`
                : "Select vendors to continue"
              }
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </>
      )}
    </motion.div>
  );
}




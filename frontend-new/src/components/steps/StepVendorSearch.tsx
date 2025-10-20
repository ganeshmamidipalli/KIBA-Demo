import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, Search, Loader2, Copy, CheckCircle2, DollarSign, Package, Clock, Star, ExternalLink } from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Textarea } from "../ui/textarea";
import { Progress } from "../ui/progress";
import { Label } from "../ui/label";
import { Badge } from "../ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { API_BASE } from "../../lib/api";
import type { SpecVariant } from "../../types";

interface Vendor {
  id: string;
  name: string;
  description: string;
  price?: string;
  priceRange?: string;
  rating?: number;
  deliveryTime?: string;
  website?: string;
  contact?: string;
  features?: string[];
  isSelected?: boolean;
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
  onNext: () => void;
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
  onNext,
  onBack,
}: StepVendorSearchProps) {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [selectedVendors, setSelectedVendors] = useState<Vendor[]>([]);
  const [parsingVendors, setParsingVendors] = useState(false);

  // Parse vendors from search output text
  useEffect(() => {
    if (searchOutputText && !searching) {
      setParsingVendors(true);
      const parsedVendors = parseVendorsFromText(searchOutputText);
      setVendors(parsedVendors);
      setParsingVendors(false);
    }
  }, [searchOutputText, searching]);

  // Parse vendors from search text
  const parseVendorsFromText = (text: string): Vendor[] => {
    const vendors: Vendor[] = [];
    const lines = text.split('\n');
    let currentVendor: Partial<Vendor> = {};
    let vendorId = 1;

    for (const line of lines) {
      const trimmedLine = line.trim();
      
      // Skip empty lines
      if (!trimmedLine) continue;
      
      // Check for vendor name patterns
      if (trimmedLine.match(/^[A-Z][a-zA-Z\s&]+(?:Inc|Corp|LLC|Ltd|Company|Technologies|Systems|Solutions|Group)$/)) {
        if (currentVendor.name) {
          vendors.push({ ...currentVendor, id: `vendor-${vendorId++}` } as Vendor);
        }
        currentVendor = { name: trimmedLine };
      }
      // Check for price patterns
      else if (trimmedLine.match(/\$[\d,]+(?:\.\d{2})?(?:\s*-\s*\$[\d,]+(?:\.\d{2})?)?/)) {
        currentVendor.price = trimmedLine;
      }
      // Check for website patterns
      else if (trimmedLine.match(/https?:\/\/[^\s]+/)) {
        currentVendor.website = trimmedLine;
      }
      // Check for rating patterns
      else if (trimmedLine.match(/\d+(?:\.\d+)?\s*\/\s*5|★\s*\d+(?:\.\d+)?/)) {
        const ratingMatch = trimmedLine.match(/(\d+(?:\.\d+)?)/);
        if (ratingMatch) {
          currentVendor.rating = parseFloat(ratingMatch[1]);
        }
      }
      // Check for delivery time patterns
      else if (trimmedLine.match(/\d+\s*(?:days?|weeks?|months?)/i)) {
        currentVendor.deliveryTime = trimmedLine;
      }
      // Everything else is description
      else if (trimmedLine.length > 10) {
        currentVendor.description = (currentVendor.description || '') + ' ' + trimmedLine;
      }
    }

    // Add the last vendor
    if (currentVendor.name) {
      vendors.push({ ...currentVendor, id: `vendor-${vendorId++}` } as Vendor);
    }

    return vendors;
  };

  // Handle vendor selection
  const handleVendorSelect = (vendor: Vendor) => {
    const isSelected = selectedVendors.some(v => v.id === vendor.id);
    if (isSelected) {
      setSelectedVendors(selectedVendors.filter(v => v.id !== vendor.id));
    } else {
      setSelectedVendors([...selectedVendors, vendor]);
    }
  };
  const [buildingQuery, setBuildingQuery] = useState(false);
  const [searchProgress, setSearchProgress] = useState(0);
  const [searchStatus, setSearchStatus] = useState("");
  const [maxResults, setMaxResults] = useState(10);

  const buildSearchQuery = async () => {
    if (selectedVariants.length === 0) return;
    
    setBuildingQuery(true);
    
    try {
      const payload = {
        product_name: productName,
        selected_variant: {
          id: selectedVariants[0].id,
          quantity: selectedVariants[0].quantity,
          metrics: selectedVariants[0].metrics,
          must: selectedVariants[0].must
        }
      };
      
      const response = await fetch(`${API_BASE}/api/search-query/build`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      
      const data = await response.json();
      const query = data.solid_query || '';
      setSearchQuery(query);
      
      if (!query) {
        const fallbackQuery = `${productName} ${Object.values(selectedVariants[0].metrics || {}).slice(0, 5).join(' ')}`;
        setSearchQuery(fallbackQuery);
      }
    } catch (error) {
      console.error('Error building search query:', error);
      const fallbackQuery = `${productName} ${Object.values(selectedVariants[0].metrics || {}).slice(0, 5).join(' ')}`;
      setSearchQuery(fallbackQuery);
    } finally {
      setBuildingQuery(false);
    }
  };

  const performWebSearch = async () => {
    if (!searchQuery.trim()) return;
    
    setSearching(true);
    setSearchOutputText("");
    setSearchProgress(0);
    setSearchStatus("Initializing search...");
    
    try {
      const progressSteps = [
        { delay: 2000, progress: 10, status: "Building search parameters..." },
        { delay: 5000, progress: 25, status: "Searching vendor databases..." },
        { delay: 15000, progress: 50, status: "Analyzing vendor options..." },
        { delay: 30000, progress: 75, status: "Validating results..." },
        { delay: 45000, progress: 90, status: "Finalizing vendor list..." },
      ];
      
      let currentStep = 0;
      const progressInterval = setInterval(() => {
        if (currentStep < progressSteps.length) {
          setSearchProgress(progressSteps[currentStep].progress);
          setSearchStatus(progressSteps[currentStep].status);
          currentStep++;
        }
      }, 3000);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 240000);
      
      const response = await fetch(`${API_BASE}/api/web_search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery,
          max_results: maxResults,
          delivery_window_days: 30
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      clearInterval(progressInterval);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      setSearchProgress(100);
      setSearchStatus("Search complete!");
      setSearchOutputText(data.output_text || "No results found.");
      
    } catch (error: any) {
      console.error('Error searching:', error);
      
      if (error.name === 'AbortError') {
        setSearchOutputText("⏱️ Search timed out. Please try again with fewer max results.");
      } else {
        setSearchOutputText(`❌ Search Error: ${error.message}`);
      }
    } finally {
      setSearching(false);
      setSearchProgress(0);
      setSearchStatus("");
    }
  };

  useEffect(() => {
    if (selectedVariants.length === 1) {
      buildSearchQuery();
    }
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
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
              <CardTitle className="text-base">Searching for:</CardTitle>
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

          {/* Search Query */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Search Query</CardTitle>
              <CardDescription>
                {buildingQuery ? "AI optimizing search terms..." : "AI-generated query • Edit if needed"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                rows={3}
                disabled={buildingQuery}
                placeholder={buildingQuery ? "Generating optimized query..." : "Enter search query..."}
                className="resize-none font-mono text-sm"
              />

              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Label htmlFor="maxResults" className="text-sm">Max results:</Label>
                  <Select
                    value={maxResults.toString()}
                    onValueChange={(value) => setMaxResults(parseInt(value))}
                    disabled={searching}
                  >
                    <SelectTrigger id="maxResults" className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="5">5</SelectItem>
                      <SelectItem value="10">10</SelectItem>
                      <SelectItem value="15">15</SelectItem>
                      <SelectItem value="20">20</SelectItem>
                      <SelectItem value="30">30</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <Button
                  onClick={performWebSearch}
                  disabled={searching || !searchQuery.trim()}
                  className="gap-2 flex-1"
                >
                  {searching ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <Search className="h-4 w-4" />
                      Search with AI
                    </>
                  )}
                </Button>
              </div>

              {searching && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{searchStatus}</span>
                    <span className="font-semibold text-primary">{searchProgress}%</span>
                  </div>
                  <Progress value={searchProgress} />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Search Results */}
          {searchOutputText && !searching && (
            <Card className="border-primary/20">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Search className="h-4 w-4 text-primary" />
                      Vendor Search Results
                    </CardTitle>
                    <CardDescription>
                      {parsingVendors ? "Parsing vendor information..." : `Found ${vendors.length} vendors`}
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      navigator.clipboard.writeText(searchOutputText);
                      alert('✅ Results copied to clipboard!');
                    }}
                    className="gap-2"
                  >
                    <Copy className="h-3 w-3" />
                    Copy Raw
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {parsingVendors ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin mr-2" />
                    <span>Parsing vendor information...</span>
                  </div>
                ) : vendors.length > 0 ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {vendors.map((vendor) => {
                        const isSelected = selectedVendors.some(v => v.id === vendor.id);
                        return (
                          <Card
                            key={vendor.id}
                            className={`cursor-pointer transition-all hover:shadow-md ${
                              isSelected 
                                ? "ring-2 ring-primary bg-primary/5" 
                                : "hover:ring-2 hover:ring-primary/30"
                            }`}
                            onClick={() => handleVendorSelect(vendor)}
                          >
                            <CardContent className="p-4">
                              <div className="flex items-start justify-between mb-3">
                                <div className="flex-1">
                                  <h3 className="font-semibold text-lg mb-1">{vendor.name}</h3>
                                  {vendor.rating && (
                                    <div className="flex items-center gap-1 mb-2">
                                      <Star className="h-4 w-4 text-yellow-500 fill-current" />
                                      <span className="text-sm text-muted-foreground">{vendor.rating}/5</span>
                                    </div>
                                  )}
                                </div>
                                <div className="flex items-center gap-2">
                                  {isSelected && (
                                    <CheckCircle2 className="h-5 w-5 text-primary" />
                                  )}
                                </div>
                              </div>
                              
                              {vendor.description && (
                                <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                                  {vendor.description}
                                </p>
                              )}
                              
                              <div className="space-y-2">
                                {vendor.price && (
                                  <div className="flex items-center gap-2">
                                    <DollarSign className="h-4 w-4 text-green-600" />
                                    <span className="font-semibold text-green-600">{vendor.price}</span>
                                  </div>
                                )}
                                
                                {vendor.deliveryTime && (
                                  <div className="flex items-center gap-2">
                                    <Clock className="h-4 w-4 text-blue-600" />
                                    <span className="text-sm text-muted-foreground">{vendor.deliveryTime}</span>
                                  </div>
                                )}
                                
                                {vendor.website && (
                                  <div className="flex items-center gap-2">
                                    <ExternalLink className="h-4 w-4 text-primary" />
                                    <a 
                                      href={vendor.website} 
                                      target="_blank" 
                                      rel="noopener noreferrer"
                                      className="text-sm text-primary hover:underline"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      Visit Website
                                    </a>
                                  </div>
                                )}
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
                            <Badge key={vendor.id} variant="secondary" className="gap-1">
                              {vendor.name}
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
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Package className="h-8 w-8 mx-auto mb-2" />
                    <p>No vendors found in search results</p>
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
              onClick={onNext}
              disabled={!searchOutputText || selectedVendors.length === 0}
              className="gap-2"
            >
              {selectedVendors.length > 0 
                ? `Continue to RFQ (${selectedVendors.length} selected)`
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




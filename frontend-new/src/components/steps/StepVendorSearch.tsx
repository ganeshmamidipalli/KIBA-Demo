import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, Search, Loader2, Copy } from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Textarea } from "../ui/textarea";
import { Progress } from "../ui/progress";
import { Label } from "../ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { API_BASE } from "../../lib/api";
import type { SpecVariant } from "../../types";

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
                    <CardDescription>Powered by AI web browsing</CardDescription>
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
                    Copy
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div
                  className="prose prose-sm dark:prose-invert max-w-none"
                  dangerouslySetInnerHTML={{
                    __html: searchOutputText
                      .replace(/\n\n/g, '</p><p>')
                      .replace(/\*\*(.*?)\*\*/g, '<strong class="text-primary font-semibold">$1</strong>')
                      .replace(/\n/g, '<br/>')
                      .replace(/^(.+)$/s, '<p>$1</p>')
                      .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-primary underline">$1</a>')
                  }}
                />
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
              disabled={!searchOutputText}
              className="gap-2"
            >
              Continue to RFQ
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </>
      )}
    </motion.div>
  );
}




import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, Loader2, Sparkles, RefreshCw, CheckCircle2 } from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { RadioGroup, RadioGroupItem } from "../ui/radio-group";
import { Label } from "../ui/label";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { Separator } from "../ui/separator";
import { Switch } from "../ui/switch";
import { Progress } from "../ui/progress";
import * as api from "../../lib/api";
import type { SpecVariant, Attachment, IntakeData, KPARecommendations } from "../../types";

interface StepSpecificationsProps {
  productName: string;
  quantity: string;
  budget: string;
  projectScope: string;
  attachments: Attachment[];
  procurementType: string;
  serviceProgram: string;
  technicalPOC: string;
  selectedProject: string;
  vendors: string[];
  variants: SpecVariant[];
  setVariants: (value: SpecVariant[]) => void;
  selectedVariants: SpecVariant[];
  setSelectedVariants: (value: SpecVariant[]) => void;
  generatingRecommendations: boolean;
  setGeneratingRecommendations: (value: boolean) => void;
  aiRecommendation: any;
  setAiRecommendation: (value: any) => void;
  // KPA One-Flow props
  kpaSessionId: string | null;
  intakeData: IntakeData | null;
  setIntakeData: (value: IntakeData | null) => void;
  followupAnswers: Record<string, string>;
  setFollowupAnswers: (value: Record<string, string>) => void;
  kpaRecommendations: KPARecommendations | null;
  setKpaRecommendations: (value: KPARecommendations | null) => void;
  onNext: () => void;
  onBack: () => void;
}

export function StepSpecifications({
  productName,
  quantity,
  budget,
  projectScope,
  attachments,
  procurementType,
  serviceProgram,
  technicalPOC,
  selectedProject,
  vendors,
  variants,
  setVariants,
  selectedVariants,
  setSelectedVariants,
  generatingRecommendations,
  setGeneratingRecommendations,
  aiRecommendation,
  setAiRecommendation,
  // KPA One-Flow props
  kpaSessionId,
  intakeData,
  setIntakeData,
  followupAnswers,
  setFollowupAnswers,
  kpaRecommendations,
  setKpaRecommendations,
  onNext,
  onBack,
}: StepSpecificationsProps) {
  
  console.log("StepSpecifications: Rendering with props:", {
    kpaSessionId,
    intakeData,
    followupAnswers,
    kpaRecommendations
  });
  
  // KPA One-Flow state
  const [submittingFollowups, setSubmittingFollowups] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [sessionVersion, setSessionVersion] = useState(0);
  const [projectSummary, setProjectSummary] = useState<string | null>(null);
  const [showProjectSummary, setShowProjectSummary] = useState(false);
  const [generatingSummary, setGeneratingSummary] = useState(false);
  
  // Convert KPA recommendations to SpecVariant format for compatibility
  const convertKPARecommendations = (kpaRecs: KPARecommendations): SpecVariant[] => {
    return kpaRecs.recommendations.map((rec, index) => ({
      id: rec.id,
      title: rec.name,
      summary: rec.value_note || "",
      quantity: parseInt(quantity) || 1,
      est_unit_price_usd: rec.estimated_price_usd || 0,
      est_total_usd: (rec.estimated_price_usd || 0) * (parseInt(quantity) || 1),
      lead_time_days: 30, // Default lead time
      rationale_summary: rec.rationale ? [rec.rationale] : []
    }));
  };

  // Generate recommendations using the existing API
  const generateRecommendations = async () => {
    if (generatingRecommendations) return;
    
    setGeneratingRecommendations(true);
    try {
      const response = await api.generateRecommendations({
        product_name: productName,
        budget_usd: parseFloat(budget),
        quantity: parseInt(quantity),
        scope_text: projectScope,
        vendors: vendors,
        uploaded_summaries: attachments.map(a => a.summary || a.text_preview || '').filter(s => s),
        project_context: {
          project_name: selectedProject,
          procurement_type: procurementType,
          service_program: serviceProgram,
          technical_poc: technicalPOC
        }
      });
      
      if (response.variants && response.variants.length > 0) {
        setVariants(response.variants);
        setAiRecommendation(response.ai_recommendation);
      }
    } catch (error) {
      console.error("Error generating recommendations:", error);
    } finally {
      setGeneratingRecommendations(false);
    }
  };

  // Handle follow-up submission
  const handleSubmitFollowups = async () => {
    if (!kpaSessionId) {
      alert("Session expired. Please go back to Step 2.");
      return;
    }

    setSubmittingFollowups(true);
    try {
      // Save the follow-up answers
      const response = await api.submitFollowups({
        session_id: kpaSessionId,
        followup_answers: followupAnswers
      });
      
      console.log("Follow-up answers saved successfully:", response);
      
      // Proceed to next step (Project Confirmation)
      onNext();
    } catch (error) {
      console.error("Error in follow-up process:", error);
      alert("Error processing follow-ups. Please try again.");
    } finally {
      setSubmittingFollowups(false);
    }
  };

  // Handle generating final recommendations after project summary confirmation
  const handleGenerateRecommendations = async () => {
    if (!kpaSessionId) {
      alert("Session expired. Please go back to Step 2.");
      return;
    }

    setGeneratingRecommendations(true);
    try {
      const response = await api.generateFinalRecommendations(kpaSessionId);
      setKpaRecommendations(response.recommendations);
      setSessionVersion(response.version || 0);
      
      // Convert to SpecVariant format and update state
      const convertedVariants = convertKPARecommendations(response.recommendations);
      setVariants(convertedVariants);
      
      // Auto-select recommended variant
      const recommendedIndex = response.recommendations.recommended_index;
      if (convertedVariants[recommendedIndex]) {
        setSelectedVariants([convertedVariants[recommendedIndex]]);
      }
      
      // Hide project summary and show recommendations
      setShowProjectSummary(false);
      
      console.log("Final recommendations generated:", response);
    } catch (error) {
      console.error("Error generating final recommendations:", error);
      alert("Error generating recommendations. Please try again.");
    } finally {
      setGeneratingRecommendations(false);
    }
  };

  // Autosave functionality with debouncing
  let saveTimer: NodeJS.Timeout;
  const debouncedSaveAnswers = useCallback((partial: Record<string, string>) => {
    const sid = localStorage.getItem("kiba3_session_id");
    if (!sid) return;

    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
      try {
        await api.patchAnswers(sid, partial);
        console.log("Answers autosaved");
      } catch (error) {
        console.error("Autosave failed:", error);
      }
    }, 400);
  }, []);

  // Handle answer changes with autosave
  const onAnswerChange = useCallback((question: string, value: string) => {
    const newAnswers = { ...followupAnswers, [question]: value };
    setFollowupAnswers(newAnswers);
    debouncedSaveAnswers({ [question]: value });
  }, [followupAnswers, setFollowupAnswers, debouncedSaveAnswers]);
  
  // Rehydrate state on mount (only if we don't already have data)
  useEffect(() => {
    const sid = localStorage.getItem("kiba3_session_id");
    console.log("StepSpecifications: Rehydrating with session ID:", sid);
    console.log("StepSpecifications: Current intake data:", intakeData);
    
    if (!sid) {
      console.log("StepSpecifications: No session ID found, skipping rehydration");
      return;
    }
    
    // Only rehydrate if we don't already have intake data
    if (intakeData) {
      console.log("StepSpecifications: Already have intake data, skipping rehydration");
      return;
    }
    
    (async () => {
      try {
        console.log("StepSpecifications: Fetching session data...");
        const data = await api.getSession(sid);
        console.log("StepSpecifications: Session data received:", data);
        
        if (data.intake) {
          console.log("StepSpecifications: Setting intake data:", data.intake);
          setIntakeData(data.intake);
        }
        if (data.answers) {
          console.log("StepSpecifications: Setting answers:", data.answers);
          setFollowupAnswers(data.answers);
        }
        if (data.recommendations) {
          console.log("StepSpecifications: Setting recommendations:", data.recommendations);
          setKpaRecommendations(data.recommendations);
          setSessionVersion(data.version || 0);
        }
      } catch (error) {
        console.error("StepSpecifications: Failed to rehydrate session:", error);
      }
    })();
  }, [intakeData, setIntakeData, setFollowupAnswers, setKpaRecommendations]);

  // Auto-generate recommendations if we have KPA data but no variants
  useEffect(() => {
    if (kpaRecommendations && variants.length === 0 && !generatingRecommendations) {
      const convertedVariants = convertKPARecommendations(kpaRecommendations);
      setVariants(convertedVariants);
      
      // Auto-select recommended variant
      const recommendedIndex = kpaRecommendations.recommended_index;
      if (convertedVariants[recommendedIndex]) {
        setSelectedVariants([convertedVariants[recommendedIndex]]);
      }
    } else if (variants.length === 0 && !generatingRecommendations && !intakeData) {
      setTimeout(() => generateRecommendations(), 500);
    }
  }, [kpaRecommendations, variants.length, generatingRecommendations, intakeData]);

  const handleContinue = () => {
    if (selectedVariants.length === 0) {
      alert("Please select at least one variant to continue");
      return;
    }
    
    // Check if we have KPA recommendations to determine selection mode
    if (kpaRecommendations) {
      const selectionMode = kpaRecommendations.selection_mode;
      if (selectionMode === "single" && selectedVariants.length !== 1) {
        alert("Please select exactly ONE variant to continue");
        return;
      } else if (selectionMode === "multi" && selectedVariants.length === 0) {
        alert("Please select at least one variant to continue");
        return;
      }
    } else {
      // Fallback to single selection for non-KPA recommendations
      if (selectedVariants.length !== 1) {
        alert("Please select exactly ONE variant to continue");
        return;
      }
    }
    
    console.log("StepSpecifications: Continuing with selected variants:", selectedVariants.length);
    onNext();
  };

  const handleSelectVariant = (variantId: string) => {
    // Check if we have KPA recommendations
    if (kpaRecommendations) {
      const rec = kpaRecommendations.recommendations.find(r => r.id === variantId);
      if (!rec) return;
      
      // Convert KPA recommendation to SpecVariant format
      const variant = {
        id: rec.id,
        title: rec.name,
        summary: rec.value_note || "",
        quantity: parseInt(quantity) || 1,
        est_unit_price_usd: rec.estimated_price_usd || 0,
        est_total_usd: (rec.estimated_price_usd || 0) * (parseInt(quantity) || 1),
        lead_time_days: 30, // Default lead time
        rationale_summary: rec.rationale ? [rec.rationale] : []
      };
      
      const selectionMode = kpaRecommendations.selection_mode;
      
      if (selectionMode === "single") {
        // Single selection - replace current selection
        setSelectedVariants([variant]);
      } else if (selectionMode === "multi") {
        // Multiple selection - toggle selection
        setSelectedVariants(prev => {
          const isSelected = prev.some(v => v.id === variantId);
          if (isSelected) {
            return prev.filter(v => v.id !== variantId);
          } else {
            return [...prev, variant];
          }
        });
      } else {
        // Default to single selection
        setSelectedVariants([variant]);
      }
    } else {
      // Handle regular variants
      const variant = variants.find(v => v.id === variantId);
      if (!variant) return;
      
      // Fallback to single selection for non-KPA recommendations
      setSelectedVariants([variant]);
    }
  };

  const handleRegenerate = async () => {
    const sid = localStorage.getItem("kiba3_session_id");
    if (!sid) {
      alert("Session expired. Please go back to Step 2.");
      return;
    }

    setRegenerating(true);
    try {
      const response = await api.regenerateRecommendations(sid);
      setKpaRecommendations(response.recommendations);
      setSessionVersion(response.version);

      // Convert to SpecVariant format and update state
      const convertedVariants = convertKPARecommendations(response.recommendations);
      setVariants(convertedVariants);

      // Auto-select recommended variant
      const recommendedIndex = response.recommendations.recommended_index;
      if (convertedVariants[recommendedIndex]) {
        setSelectedVariants([convertedVariants[recommendedIndex]]);
      }

      console.log("Recommendations regenerated:", response);
    } catch (error) {
      console.error("Error regenerating recommendations:", error);
      alert("Error regenerating recommendations. Please try again.");
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* KPA One-Flow Follow-up Questions */}
      {intakeData && intakeData.missing_info_questions.length > 0 && (
        <Card className="border-blue-500/30 bg-blue-500/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Sparkles className="h-5 w-5 text-blue-500" />
              We need a few more details
            </CardTitle>
            <CardDescription>{intakeData.requirements_summary}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {intakeData.missing_info_questions.map((question, index) => (
              <div key={index} className="space-y-2">
                <Label htmlFor={`followup-${index}`} className="text-sm font-medium">
                  {question}
                </Label>
                <Input
                  id={`followup-${index}`}
                  value={followupAnswers[question] || ""}
                  onChange={(e) => onAnswerChange(question, e.target.value)}
                  placeholder="Your answer..."
                  className="w-full"
                />
              </div>
            ))}
            <div className="flex justify-end pt-4">
              <Button
                onClick={handleSubmitFollowups}
                disabled={submittingFollowups}
                className="gap-2"
              >
                {submittingFollowups ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving Answers...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Submit & Continue
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Show recommendations if we have them */}
      {(variants.length > 0 || kpaRecommendations) && (
        <>
          {/* Recommendations Ready Card */}
          {variants.length > 0 && (
            <Card className="border-green-500/30 bg-green-500/5">
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                      <CheckCircle2 className="h-6 w-6 text-green-600" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold mb-1">Recommendations Ready!</h3>
                    <p className="text-sm text-muted-foreground">
                      We've generated {variants.length} carefully optimized variants. Select your preferred option below.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* AI Recommendation */}
          {aiRecommendation && (
            <Card className="border-purple-500/30 bg-purple-500/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Sparkles className="h-5 w-5 text-purple-500" />
                  AI Recommendation
                </CardTitle>
                <CardDescription>{aiRecommendation.reason}</CardDescription>
              </CardHeader>
            </Card>
          )}

          {/* KPA Recommendations with Regenerate Button */}
          {kpaRecommendations && kpaRecommendations.recommendations && kpaRecommendations.recommendations.length > 0 && (
            <Card className="border-primary/40 bg-gradient-to-r from-primary/10 to-primary/5">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg font-semibold">AI Recommendations (best → least)</CardTitle>
                    <CardDescription>
                      Ranked by overall fit. Score reflects performance, budget alignment, reliability, availability, and TCO.
                      {sessionVersion > 0 && (
                        <span className="block mt-1 text-xs text-muted-foreground">
                          Version {sessionVersion} • Last updated: {new Date().toLocaleTimeString()}
                        </span>
                      )}
                    </CardDescription>
                  </div>
                  <Button
                    onClick={handleRegenerate}
                    disabled={regenerating}
                    variant="outline"
                    size="sm"
                    className="gap-2"
                  >
                    {regenerating ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Regenerating...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-4 w-4" />
                        Regenerate with AI
                      </>
                    )}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {kpaRecommendations.recommendations.map((rec: any, idx: number) => {
                  const isSelected = selectedVariants.some(v => v.id === rec.id);
                  const isMultiMode = kpaRecommendations.selection_mode === "multi";
                  
                  return (
                    <Card 
                      key={rec.id} 
                      className={`cursor-pointer transition-all ${
                        isSelected 
                          ? "ring-2 ring-primary bg-primary/5" 
                          : idx === kpaRecommendations.recommended_index 
                            ? "ring-2 ring-primary/50" 
                            : "hover:ring-2 hover:ring-primary/30"
                      }`}
                      onClick={() => handleSelectVariant(rec.id)}
                    >
                      <CardContent className="p-5">
                        <div className="flex items-start justify-between">
                          <div className="space-y-2 flex-1">
                            <div className="flex items-center gap-3">
                              {isMultiMode ? (
                                <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                                  isSelected 
                                    ? "bg-primary border-primary text-primary-foreground" 
                                    : "border-muted-foreground"
                                }`}>
                                  {isSelected && <CheckCircle2 className="w-3 h-3" />}
                                </div>
                              ) : (
                                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                                  isSelected 
                                    ? "bg-primary border-primary text-primary-foreground" 
                                    : "border-muted-foreground"
                                }`}>
                                  {isSelected && <div className="w-2 h-2 rounded-full bg-primary-foreground" />}
                                </div>
                              )}
                              <h4 className="text-base font-semibold">{rec.name}</h4>
                              <span className="text-xs px-2 py-0.5 rounded bg-muted">
                                Score: {Math.round(rec.score)}
                              </span>
                              {idx === kpaRecommendations.recommended_index && (
                                <span className="text-xs px-2 py-0.5 rounded bg-primary text-primary-foreground">Recommended</span>
                              )}
                              {rec.meets_budget ? (
                                <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-800">Within Budget</span>
                              ) : (
                                <span className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-800">Over Budget</span>
                              )}
                            </div>
                            {rec.value_note && <p className="text-sm text-muted-foreground">{rec.value_note}</p>}
                            {rec.rationale && (
                              <>
                                <p className="text-xs font-semibold mt-2">Why this pick:</p>
                                <p className="text-xs text-muted-foreground">{rec.rationale}</p>
                              </>
                            )}
                            {Array.isArray(rec.specs) && rec.specs.length > 0 && (
                              <div className="mt-2">
                                <p className="text-xs font-semibold mb-1">Key Specifications:</p>
                                <ul className="text-xs text-muted-foreground list-disc ml-5 space-y-1">
                                  {rec.specs.map((spec: string, i: number) => <li key={i}>{spec}</li>)}
                                </ul>
                              </div>
                            )}
                          </div>
                          <div className="text-right min-w-[180px] ml-4">
                            <div className="text-sm">
                              <span className="font-medium block">Est. Unit Price</span>
                              <span className="text-lg font-semibold">${rec.estimated_price_usd?.toLocaleString() ?? "—"}</span>
                            </div>
                            <div className="text-sm mt-2">
                              <span className="font-medium block">Total Cost</span>
                              <span className="text-lg font-semibold">
                                ${((rec.estimated_price_usd || 0) * (parseInt(quantity) || 1)).toLocaleString()}
                              </span>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Variant Selection - Only show if no KPA recommendations */}
          {!kpaRecommendations && (
            <Card>
              <CardHeader>
                <CardTitle>
                  {kpaRecommendations?.selection_mode === "multi" 
                    ? "Select Variants" 
                    : "Select ONE Variant"}
                </CardTitle>
                <CardDescription>
                  {kpaRecommendations?.selection_mode === "multi" ? (
                    selectedVariants.length > 0
                      ? `✓ Selected ${selectedVariants.length} variant(s): ${selectedVariants.map(v => v.title).join(", ")}`
                      : "Choose one or more specification variants that best fit your needs"
                  ) : (
                    selectedVariants.length === 1
                      ? `✓ Selected: ${selectedVariants[0].title}`
                      : "Choose the specification variant that best fits your needs"
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {variants.map((variant) => {
                    const isSelected = selectedVariants.some(v => v.id === variant.id);
                    const isMultiMode = kpaRecommendations?.selection_mode === "multi";
                    
                    return (
                      <Card
                        key={variant.id}
                        className={`cursor-pointer transition-all ${
                          isSelected 
                            ? "border-primary bg-primary/5 ring-2 ring-primary/20" 
                            : "hover:border-primary/50 hover:bg-primary/2"
                        }`}
                        onClick={() => handleSelectVariant(variant.id)}
                      >
                        <CardContent className="pt-6">
                          <div className="flex items-start gap-4">
                            {isMultiMode ? (
                              <div className={`w-5 h-5 rounded border-2 flex items-center justify-center mt-1 ${
                                isSelected 
                                  ? "bg-primary border-primary text-primary-foreground" 
                                  : "border-muted-foreground"
                              }`}>
                                {isSelected && <CheckCircle2 className="w-3 h-3" />}
                              </div>
                            ) : (
                              <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mt-1 ${
                                isSelected 
                                  ? "bg-primary border-primary text-primary-foreground" 
                                  : "border-muted-foreground"
                              }`}>
                                {isSelected && <div className="w-2 h-2 rounded-full bg-primary-foreground" />}
                              </div>
                            )}
                            <div className="flex-1 space-y-3">
                              <Label htmlFor={variant.id} className="text-base font-semibold cursor-pointer">
                                {variant.title}
                              </Label>
                              <p className="text-sm text-muted-foreground">{variant.summary}</p>
                              
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
                                <div>
                                  <p className="text-xs text-muted-foreground">Unit Price</p>
                                  <p className="text-sm font-semibold">${variant.est_unit_price_usd.toLocaleString()}</p>
                                </div>
                                <div>
                                  <p className="text-xs text-muted-foreground">Total Cost</p>
                                  <p className="text-sm font-semibold">${variant.est_total_usd.toLocaleString()}</p>
                                </div>
                                <div>
                                  <p className="text-xs text-muted-foreground">Quantity</p>
                                  <p className="text-sm font-semibold">{variant.quantity}</p>
                                </div>
                                <div>
                                  <p className="text-xs text-muted-foreground">Lead Time</p>
                                  <p className="text-sm font-semibold">{variant.lead_time_days} days</p>
                                </div>
                              </div>

                              {variant.rationale_summary && variant.rationale_summary.length > 0 && (
                                <div className="pt-2">
                                  <p className="text-xs font-semibold mb-1">Rationale:</p>
                                  <ul className="text-xs text-muted-foreground space-y-1">
                                    {variant.rationale_summary.map((item, idx) => (
                                      <li key={idx}>• {item}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>

                <div className="mt-6 flex justify-center">
                  <Button
                    onClick={() => {
                      setVariants([]);
                      setTimeout(() => generateRecommendations(), 100);
                    }}
                    variant="outline"
                    size="sm"
                  >
                    Regenerate with AI
                  </Button>
                </div>
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
              onClick={handleContinue}
              disabled={
                kpaRecommendations?.selection_mode === "multi" 
                  ? selectedVariants.length === 0
                  : selectedVariants.length !== 1
              }
              className="gap-2"
            >
              {kpaRecommendations?.selection_mode === "multi" 
                ? `Continue with ${selectedVariants.length} selected`
                : "Continue to Vendor Search"
              }
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </>
      )}
    </motion.div>
  );
}
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Moon, Sun, CheckCircle2, Circle } from "lucide-react";
import { useTheme } from "./components/theme-provider";
import { Button } from "./components/ui/button";
import { Progress } from "./components/ui/progress";
import { cn } from "./lib/utils";
import type { SpecVariant, Attachment, RFQResult, IntakeData, KPARecommendations } from "./types";

// Step Components (to be created)
import { StepProjectContext } from "./components/steps/StepProjectContext";
import { StepProductDetails } from "./components/steps/StepProductDetails";
import { StepProjectSummary } from "./components/steps/StepProjectSummary";
import { StepSpecifications } from "./components/steps/StepSpecifications";
import { StepVendorSearch } from "./components/steps/StepVendorSearch";
import { StepRFQ } from "./components/steps/StepRFQ";

const STEPS = [
  { id: 1, label: "Project Context", component: StepProjectContext },
  { id: 2, label: "Product + Industry", component: StepProductDetails },
  { id: 3, label: "AI Follow-up Questions", component: StepSpecifications },
  { id: 4, label: "Project Confirmation", component: StepProjectSummary },
  { id: 5, label: "Specifications", component: StepSpecifications },
  { id: 6, label: "Search", component: StepVendorSearch },
  { id: 7, label: "RFQ", component: StepRFQ },
];

export default function App() {
  const { theme, setTheme } = useTheme();
  const [currentStep, setCurrentStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  // Step 1: Project Context
  const [procurementType, setProcurementType] = useState("");
  const [serviceProgram, setServiceProgram] = useState("");
  const [technicalPOC, setTechnicalPOC] = useState("");
  const [selectedProject, setSelectedProject] = useState("");
  const [popStart, setPopStart] = useState("");
  const [popCompletion, setPopCompletion] = useState("");

  // Step 2: Product Details
  const [productName, setProductName] = useState("");
  const [category, setCategory] = useState("");
  const [quantity, setQuantity] = useState("");
  const [budget, setBudget] = useState("");
  const [projectScope, setProjectScope] = useState("");
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [vendors, setVendors] = useState<string[]>([]);

  // Step 3: Specifications
  const [variants, setVariants] = useState<SpecVariant[]>([]);
  const [selectedVariants, setSelectedVariants] = useState<SpecVariant[]>([]);
  const [generatingRecommendations, setGeneratingRecommendations] = useState(false);
  const [aiRecommendation, setAiRecommendation] = useState<any>(null);

  // KPA One-Flow state
  const [kpaSessionId, setKpaSessionId] = useState<string | null>(null);
  const [intakeData, setIntakeData] = useState<IntakeData | null>(null);
  const [followupAnswers, setFollowupAnswers] = useState<Record<string, string>>({});
  const [kpaRecommendations, setKpaRecommendations] = useState<KPARecommendations | null>(null);

  // Step 4: Vendor Search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOutputText, setSearchOutputText] = useState("");
  const [searching, setSearching] = useState(false);

  // Step 5: RFQ
  const [generatedRFQ, setGeneratedRFQ] = useState<RFQResult | null>(null);
  const [generatingRFQ, setGeneratingRFQ] = useState(false);

  const progressPercent = (currentStep / STEPS.length) * 100;

  const handleNext = () => {
    console.log("App: handleNext called, current step:", currentStep);
    console.log("App: KPA One-Flow state:", {
      kpaSessionId,
      intakeData,
      followupAnswers,
      kpaRecommendations
    });
    
    if (!completedSteps.includes(currentStep)) {
      setCompletedSteps([...completedSteps, currentStep]);
    }
    if (currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const jumpToStep = (step: number) => {
    // Can only jump to completed steps or next step
    if (completedSteps.includes(step - 1) || step === 1) {
      setCurrentStep(step);
    }
  };

  return (
    <div className="min-h-screen bg-background transition-colors duration-300">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-lg font-bold text-primary-foreground">K</span>
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight">
                KIBA Procurement AI
              </h1>
              <p className="text-xs text-muted-foreground">
                Knowmadics Assistant
              </p>
            </div>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="rounded-full"
          >
            {theme === "dark" ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </Button>
        </div>
      </header>

      {/* Progress Bar */}
      <div className="border-b bg-muted/30">
        <div className="container py-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">
              Step {currentStep} of {STEPS.length}
            </span>
            <span className="text-xs text-muted-foreground">
              {Math.round(progressPercent)}% Complete
            </span>
          </div>
          <Progress value={progressPercent} className="h-1.5" />
        </div>
      </div>

      <div className="container py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar - Steps Navigation */}
          <div className="lg:col-span-1">
            <div className="sticky top-24 space-y-1">
              {STEPS.map((step) => {
                const isActive = currentStep === step.id;
                const isCompleted = completedSteps.includes(step.id);
                const isLocked = !isCompleted && step.id > currentStep;

                return (
                  <motion.button
                    key={step.id}
                    onClick={() => jumpToStep(step.id)}
                    disabled={isLocked}
                    whileHover={!isLocked ? { x: 4 } : {}}
                    whileTap={!isLocked ? { scale: 0.98 } : {}}
                    className={cn(
                      "w-full flex items-center gap-3 p-3 rounded-lg text-left transition-all",
                      isActive && "bg-primary/10 border border-primary/20",
                      isCompleted && !isActive && "bg-muted/50",
                      isLocked && "opacity-50 cursor-not-allowed",
                      !isActive && !isCompleted && !isLocked && "hover:bg-muted/50"
                    )}
                  >
                    <div
                      className={cn(
                        "flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center transition-colors",
                        isActive && "bg-primary text-primary-foreground",
                        isCompleted && !isActive && "bg-primary/20 text-primary",
                        !isActive && !isCompleted && "bg-muted text-muted-foreground"
                      )}
                    >
                      {isCompleted ? (
                        <CheckCircle2 className="h-4 w-4" />
                      ) : (
                        <Circle className="h-4 w-4" fill={isActive ? "currentColor" : "none"} />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div
                        className={cn(
                          "text-sm font-medium truncate",
                          isActive && "text-foreground",
                          isCompleted && !isActive && "text-muted-foreground",
                          !isActive && !isCompleted && "text-muted-foreground"
                        )}
                      >
                        {step.label}
                      </div>
                    </div>
                  </motion.button>
                );
              })}
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentStep}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-6"
              >
                {/* Render current step component */}
                {currentStep === 1 && (
                  <StepProjectContext
                    procurementType={procurementType}
                    setProcurementType={setProcurementType}
                    serviceProgram={serviceProgram}
                    setServiceProgram={setServiceProgram}
                    technicalPOC={technicalPOC}
                    setTechnicalPOC={setTechnicalPOC}
                    selectedProject={selectedProject}
                    setSelectedProject={setSelectedProject}
                    popStart={popStart}
                    setPopStart={setPopStart}
                    popCompletion={popCompletion}
                    setPopCompletion={setPopCompletion}
                    onNext={handleNext}
                  />
                )}

                {currentStep === 2 && (
                  <StepProductDetails
                    productName={productName}
                    setProductName={setProductName}
                    category={category}
                    setCategory={setCategory}
                    quantity={quantity}
                    setQuantity={setQuantity}
                    budget={budget}
                    setBudget={setBudget}
                    projectScope={projectScope}
                    setProjectScope={setProjectScope}
                    attachments={attachments}
                    setAttachments={setAttachments}
                    vendors={vendors}
                    setVendors={setVendors}
                    // KPA One-Flow props
                    kpaSessionId={kpaSessionId}
                    setKpaSessionId={setKpaSessionId}
                    setIntakeData={setIntakeData}
                    projectContext={{
                      project_name: selectedProject,
                      procurement_type: procurementType,
                      service_program: serviceProgram,
                      technical_poc: technicalPOC
                    }}
                    onNext={handleNext}
                    onBack={handleBack}
                  />
                )}

                {currentStep === 3 && (
                  <StepSpecifications
                    productName={productName}
                    quantity={quantity}
                    budget={budget}
                    projectScope={projectScope}
                    attachments={attachments}
                    procurementType={procurementType}
                    serviceProgram={serviceProgram}
                    technicalPOC={technicalPOC}
                    selectedProject={selectedProject}
                    vendors={vendors}
                    variants={variants}
                    setVariants={setVariants}
                    selectedVariants={selectedVariants}
                    setSelectedVariants={setSelectedVariants}
                    generatingRecommendations={generatingRecommendations}
                    setGeneratingRecommendations={setGeneratingRecommendations}
                    aiRecommendation={aiRecommendation}
                    setAiRecommendation={setAiRecommendation}
                    // KPA One-Flow props
                    kpaSessionId={kpaSessionId}
                    intakeData={intakeData}
                    setIntakeData={setIntakeData}
                    followupAnswers={followupAnswers}
                    setFollowupAnswers={setFollowupAnswers}
                    kpaRecommendations={kpaRecommendations}
                    setKpaRecommendations={setKpaRecommendations}
                    onNext={handleNext}
                    onBack={handleBack}
                  />
                )}

                {currentStep === 4 && (
                  <StepProjectSummary
                    procurementType={procurementType}
                    serviceProgram={serviceProgram}
                    technicalPOC={technicalPOC}
                    selectedProject={selectedProject}
                    popStart={popStart}
                    popCompletion={popCompletion}
                    productName={productName}
                    category={category}
                    quantity={quantity}
                    budget={budget}
                    projectScope={projectScope}
                    attachments={attachments}
                    vendors={vendors}
                    // KPA One-Flow props
                    kpaSessionId={kpaSessionId}
                    setKpaSessionId={setKpaSessionId}
                    setIntakeData={setIntakeData}
                    // Callbacks
                    onEdit={(step) => setCurrentStep(step)}
                    onConfirm={handleNext}
                    onBack={handleBack}
                  />
                )}

                {currentStep === 5 && (
                  <StepSpecifications
                    productName={productName}
                    quantity={quantity}
                    budget={budget}
                    projectScope={projectScope}
                    attachments={attachments}
                    procurementType={procurementType}
                    serviceProgram={serviceProgram}
                    technicalPOC={technicalPOC}
                    selectedProject={selectedProject}
                    vendors={vendors}
                    variants={variants}
                    setVariants={setVariants}
                    selectedVariants={selectedVariants}
                    setSelectedVariants={setSelectedVariants}
                    generatingRecommendations={generatingRecommendations}
                    setGeneratingRecommendations={setGeneratingRecommendations}
                    aiRecommendation={aiRecommendation}
                    setAiRecommendation={setAiRecommendation}
                    // KPA One-Flow props
                    kpaSessionId={kpaSessionId}
                    intakeData={intakeData}
                    setIntakeData={setIntakeData}
                    followupAnswers={followupAnswers}
                    setFollowupAnswers={setFollowupAnswers}
                    kpaRecommendations={kpaRecommendations}
                    setKpaRecommendations={setKpaRecommendations}
                    onNext={handleNext}
                    onBack={handleBack}
                  />
                )}

                {currentStep === 6 && (
                  <StepVendorSearch
                    productName={productName}
                    selectedVariants={selectedVariants}
                    searchQuery={searchQuery}
                    setSearchQuery={setSearchQuery}
                    searchOutputText={searchOutputText}
                    setSearchOutputText={setSearchOutputText}
                    searching={searching}
                    setSearching={setSearching}
                    onNext={handleNext}
                    onBack={handleBack}
                  />
                )}

                {currentStep === 7 && (
                  <StepRFQ
                    selectedProject={selectedProject}
                    procurementType={procurementType}
                    serviceProgram={serviceProgram}
                    technicalPOC={technicalPOC}
                    popStart={popStart}
                    popCompletion={popCompletion}
                    productName={productName}
                    category={category}
                    quantity={quantity}
                    budget={budget}
                    projectScope={projectScope}
                    attachments={attachments}
                    selectedVariants={selectedVariants}
                    searchOutputText={searchOutputText}
                    vendors={vendors}
                    generatedRFQ={generatedRFQ}
                    setGeneratedRFQ={setGeneratedRFQ}
                    generatingRFQ={generatingRFQ}
                    setGeneratingRFQ={setGeneratingRFQ}
                    onBack={handleBack}
                  />
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}




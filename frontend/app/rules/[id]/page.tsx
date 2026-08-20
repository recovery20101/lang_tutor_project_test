"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Header } from "@/components/ui/header";
import { useAuth } from "@/context/auth-context";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  XCircle,
  HelpCircle,
  BookOpen,
  CheckSquare,
  ListPlus,
  PenTool,
  Sparkles,
  PlusCircle,
  Loader2
} from "lucide-react";
import { useRouter } from "next/navigation";

interface RuleListItem {
  chunk_id: string;
  display_title?: string;
}

interface BaseExercise {
  id: number;
  type: string;
  question: string;
  correct_answer: string;
  translation: string;
}

interface FillInTheBlankExercise extends BaseExercise {
  type: "fill_in_the_blank";
}

interface MultipleChoiceExercise extends BaseExercise {
  type: "multiple_choice";
  options: string[];
}

interface FreeResponseExercise extends BaseExercise {
  type: "free_response";
}

type Exercise = FillInTheBlankExercise | MultipleChoiceExercise | FreeResponseExercise;

interface Rule {
  chunk_id: string;
  level: string;
  lang: string;
  topic: string;
  subtopic: string;
  content: string;
  title: string;
  display_title?: string;
  related_rules?: RuleListItem[];
  exercises?: Exercise[];
  next_chunk_id: string | null;
}

interface CheckResponse {
  score: number;
  correct_version: string;
  explanation: string | object;
}

interface CheckRequestBody {
  chunk_id: string;
  user_answer: string;
  lang: string;
  exercise_type?: string;
  original_question?: string;
  correct_answer_example?: string;
  exercise_id?: number;
}

async function getRule(id: string, isAuthenticated: boolean, token: string | null): Promise<Rule | null> {
  const headers: HeadersInit = {};
  if (isAuthenticated && token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/rule/${id}`, {
    cache: 'no-store',
    headers: headers,
  });
  if (!res.ok) return null;
  return res.json();
}

/* Component for rendering exercise feedback with gamification and coloring */
function ExerciseFeedback({ feedback }: { feedback: CheckResponse }) {
  const isPerfect = feedback.score === 10;
  const isGood = feedback.score >= 5 && feedback.score < 10;

  return (
    <div className={`mt-4 p-4 rounded-xl border text-sm transition-all duration-300 ${
      isPerfect
        ? "bg-emerald-50 border-emerald-100 text-emerald-900"
        : isGood
          ? "bg-amber-50 border-amber-100 text-amber-950"
          : "bg-rose-50 border-rose-100 text-rose-900"
    }`}>
      <div className="flex items-center space-x-2 mb-2">
        {isPerfect ? (
          <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />
        ) : (
          <XCircle className="w-5 h-5 text-rose-500 shrink-0" />
        )}
        <span className="font-bold text-base">Score: {feedback.score}/10</span>
      </div>

      {feedback.correct_version && (
        <div className="mt-1 bg-white/60 p-2 rounded-lg border border-black/5">
          <span className="font-medium opacity-80">Correct Answer:</span>{" "}
          <strong className="font-semibold">{feedback.correct_version}</strong>
        </div>
      )}

      {feedback.explanation && (
        <p className="mt-2 text-xs leading-relaxed opacity-90">
          <span className="font-semibold block mb-0.5">Explanation:</span>
          {typeof feedback.explanation === 'string' ? feedback.explanation : JSON.stringify(feedback.explanation)}
        </p>
      )}
    </div>
  );
}

/* 1. Fill In The Blank */
function FillInTheBlankExerciseComponent({ exercise, ruleChunkId, isAuthenticated, token }: { exercise: FillInTheBlankExercise, ruleChunkId: string, isAuthenticated: boolean, token: string | null }) {
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<CheckResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setLoading(true); setFeedback(null); setError(null);
    console.log("FillInTheBlankExerciseComponent: Submitting exercise:", {
      exerciseId: exercise.id,
      exerciseQuestion: exercise.question,
      userAnswer: answer,
      ruleChunkId: ruleChunkId
    });
    try {
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (isAuthenticated && token) headers['Authorization'] = `Bearer ${token}`;

      const isDynamicExercise = exercise.id <= 0;

      const endpoint = isDynamicExercise ? `${process.env.NEXT_PUBLIC_API_URL}/check/dynamic_exercise` : `${process.env.NEXT_PUBLIC_API_URL}/check`;
      const bodyData: CheckRequestBody = {
        chunk_id: ruleChunkId,
        user_answer: answer,
        lang: "en"
      };

      if (isDynamicExercise) {
        bodyData.exercise_type = exercise.type;
        bodyData.original_question = exercise.question;
        bodyData.correct_answer_example = exercise.correct_answer;
      } else {
        bodyData.exercise_id = exercise.id;
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(bodyData),
      });
      if (!res.ok) {
        const errorData = await res.json();
        setError(errorData.detail || "Validation error.");
        return;
      }
      setFeedback(await res.json());
    } catch {
      setError("Network error. Please check your connection.");
    } finally { setLoading(false); }
  };

  return (
    <Card className="border border-slate-100 bg-white shadow-sm rounded-2xl overflow-hidden mb-5">
      <CardHeader className="bg-slate-50/60 pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-2 text-indigo-600">
          <Sparkles className="w-4 h-4" />
          <CardTitle className="text-sm font-bold uppercase tracking-wider">Fill in the Blank</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <p className="text-lg font-medium text-slate-800 mb-3 bg-slate-50 p-3 rounded-xl border border-slate-100/70">
          {exercise.question.replace("___", " ______ ")}
        </p>
        <p className="text-xs text-slate-400 italic mb-3">Translation: {exercise.translation}</p>

        <div className="flex gap-2">
          <Input
            type="text"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Type the missing word..."
            className="rounded-xl border-slate-200 focus-visible:ring-indigo-500 h-11"
            disabled={loading}
          />
          <Button
            onClick={handleSubmit}
            disabled={loading || !answer.trim()}
            className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl h-11 px-5 font-medium transition-all shrink-0"
          >
            {loading ? "..." : "Check"}
          </Button>
        </div>
        {error && <div className="mt-3 p-3 rounded-xl bg-rose-50 text-rose-600 border border-rose-100 text-xs">{error}</div>}
        {feedback && <ExerciseFeedback feedback={feedback} />}
      </CardContent>
    </Card>
  );
}

/* 2. Multiple Choice */
function MultipleChoiceExerciseComponent({ exercise, ruleChunkId, isAuthenticated, token }: { exercise: MultipleChoiceExercise, ruleChunkId: string, isAuthenticated: boolean, token: string | null }) {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<CheckResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setLoading(true); setFeedback(null); setError(null);
    console.log("MultipleChoiceExerciseComponent: Submitting exercise:", {
      exerciseId: exercise.id,
      exerciseQuestion: exercise.question,
      userAnswer: selectedOption,
      ruleChunkId: ruleChunkId
    });
    try {
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (isAuthenticated && token) headers['Authorization'] = `Bearer ${token}`;

      const isDynamicExercise = exercise.id <= 0;

      const endpoint = isDynamicExercise ? `${process.env.NEXT_PUBLIC_API_URL}/check/dynamic_exercise` : `${process.env.NEXT_PUBLIC_API_URL}/check`;
      const bodyData: CheckRequestBody = {
        chunk_id: ruleChunkId,
        user_answer: selectedOption || "",
        lang: "en"
      };

      if (isDynamicExercise) {
        bodyData.exercise_type = exercise.type;
        bodyData.original_question = exercise.question;
        bodyData.correct_answer_example = exercise.correct_answer;
      } else {
        bodyData.exercise_id = exercise.id;
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(bodyData),
      });
      if (!res.ok) {
        const errorData = await res.json();
        setError(errorData.detail || "Validation error.");
        return;
      }
      setFeedback(await res.json());
    } catch {
      setError("Network error.");
    } finally { setLoading(false); }
  };

  return (
    <Card className="border border-slate-100 bg-white shadow-sm rounded-2xl overflow-hidden mb-5">
      <CardHeader className="bg-slate-50/60 pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-2 text-emerald-600">
          <HelpCircle className="w-4 h-4" />
          <CardTitle className="text-sm font-bold uppercase tracking-wider">Multiple Choice</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <p className="text-lg font-medium text-slate-800 mb-1">{exercise.question}</p>
        <p className="text-xs text-slate-400 italic mb-4">Translation: {exercise.translation}</p>

        <RadioGroup onValueChange={setSelectedOption} value={selectedOption || ""} className="space-y-2 mb-4">
          {exercise.options.map((option, index) => {
            const isSelected = selectedOption === option;
            return (
              <label
                key={index}
                className={`flex items-center space-x-3 p-3 rounded-xl border cursor-pointer transition-all ${
                  isSelected
                    ? "border-indigo-600 bg-indigo-50/40 font-medium"
                    : "border-slate-100 bg-slate-50/30 hover:bg-slate-50"
                }`}
              >
                <RadioGroupItem value={option} id={`opt-${index}`} disabled={loading} className="text-indigo-600 focus:ring-indigo-500" />
                <span className="text-sm text-slate-700">{option}</span>
              </label>
            );
          })}
        </RadioGroup>

        <Button
          onClick={handleSubmit}
          disabled={loading || !selectedOption}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl h-11 font-medium transition-all"
        >
          {loading ? "Checking..." : "Submit Answer"}
        </Button>
        {error && <div className="mt-3 p-3 rounded-xl bg-rose-50 text-rose-600 border border-rose-100 text-xs">{error}</div>}
        {feedback && <ExerciseFeedback feedback={feedback} />}
      </CardContent>
    </Card>
  );
}

/* 3. Free Response */
function FreeResponseExerciseComponent({ exercise, ruleChunkId, isAuthenticated, token }: { exercise: FreeResponseExercise, ruleChunkId: string, isAuthenticated: boolean, token: string | null }) {
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<CheckResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setLoading(true); setFeedback(null); setError(null);
    console.log("FreeResponseExerciseComponent: Submitting exercise:", {
      exerciseId: exercise.id,
      exerciseQuestion: exercise.question,
      userAnswer: answer,
      ruleChunkId: ruleChunkId
    });
    try {
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (isAuthenticated && token) headers['Authorization'] = `Bearer ${token}`;

      const isDynamicExercise = exercise.id <= 0;

      const endpoint = isDynamicExercise ? `${process.env.NEXT_PUBLIC_API_URL}/check/dynamic_exercise` : `${process.env.NEXT_PUBLIC_API_URL}/check`;
      const bodyData: CheckRequestBody = {
        chunk_id: ruleChunkId,
        user_answer: answer,
        lang: "en"
      };

      if (isDynamicExercise) {
        bodyData.exercise_type = exercise.type;
        bodyData.original_question = exercise.question;
        bodyData.correct_answer_example = exercise.correct_answer;
      } else {
        bodyData.exercise_id = exercise.id;
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(bodyData),
      });
      if (!res.ok) {
        const errorData = await res.json();
        setError(errorData.detail || "Validation error.");
        return;
      }
      setFeedback(await res.json());
    } catch {
      setError("Network error.");
    } finally { setLoading(false) }
  };

  return (
    <Card className="border border-slate-100 bg-white shadow-sm rounded-2xl overflow-hidden mb-5">
      <CardHeader className="bg-slate-50/60 pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-2 text-purple-600">
          <BookOpen className="w-4 h-4" />
          <CardTitle className="text-sm font-bold uppercase tracking-wider">Free Response</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <p className="text-lg font-medium text-slate-800 mb-1">{exercise.question}</p>
        <p className="text-xs text-slate-400 italic mb-3">Translation: {exercise.translation}</p>

        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Write your translation or answer in Spanish..."
          className="flex min-h-[90px] w-full rounded-xl border border-slate-200 bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 mb-3"
          disabled={loading}
        />
        <Button onClick={handleSubmit} disabled={loading || !answer.trim()} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl h-11 font-medium transition-all">
          {loading ? "AI Checking..." : "Check Free Response"}
        </Button>
        {error && <div className="mt-3 p-3 rounded-xl bg-rose-50 text-rose-600 border border-rose-100 text-xs">{error}</div>}
        {feedback && <ExerciseFeedback feedback={feedback} />}
      </CardContent>
    </Card>
  );
}


/* Main Rule Page */
export default function RulePage({ params: paramsPromise }: { params: Promise<{ id: string }> }) {
  const { isAuthenticated, token} = useAuth();
  const router = useRouter();
  const [rule, setRule] = useState<Rule | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolvedParams, setResolvedParams] = useState<{ id: string } | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);

  // States for tracking current index in each exercise group
  const [currentFillIdx, setCurrentFillIdx] = useState(0);
  const [currentChoiceIdx, setCurrentChoiceIdx] = useState(0);
  const [currentFreeIdx, setCurrentFreeIdx] = useState(0);

  // States for storing dynamically loaded exercises
  const [dynamicFillExercises, setDynamicFillExercises] = useState<FillInTheBlankExercise[]>([]);
  const [dynamicChoiceExercises, setDynamicChoiceExercises] = useState<MultipleChoiceExercise[]>([]);
  const [dynamicFreeExercises, setDynamicFreeExercises] = useState<FreeResponseExercise[]>([]);

  // Loading states for "Generate more" buttons
  const [loadingMoreFill, setLoadingMoreFill] = useState(false);
  const [loadingMoreChoice, setLoadingMoreChoice] = useState(false);
  const [loadingMoreFree, setLoadingMoreFree] = useState(false);

  // Loading state when clicking "Next rule" for Overview blocks
  const [isRedirecting, setIsRedirecting] = useState(false);

  // Check if current block is purely an overview (no exercises)
  const isOverview =
    dynamicFillExercises.length === 0 &&
    dynamicChoiceExercises.length === 0 &&
    dynamicFreeExercises.length === 0;

  useEffect(() => {
    const resolveParams = async () => { setResolvedParams(await paramsPromise); };
    resolveParams();
  }, [paramsPromise]);

  useEffect(() => {
    if (!resolvedParams) return;
    const fetchRuleAndNext = async () => {
      setLoading(true); setPageError(null);
      try {
        const fetchedRule = await getRule(resolvedParams.id, isAuthenticated, token);
        if (!fetchedRule) { setPageError("Failed to load the rule."); setLoading(false); return; }
        setRule(fetchedRule);
        // Initialize dynamic exercises with backend data
        setDynamicFillExercises(fetchedRule.exercises?.filter(e => e.type === "fill_in_the_blank") as FillInTheBlankExercise[] || []);
        setDynamicChoiceExercises(fetchedRule.exercises?.filter(e => e.type === "multiple_choice") as MultipleChoiceExercise[] || []);
        setDynamicFreeExercises(fetchedRule.exercises?.filter(e => e.type === "free_response") as FreeResponseExercise[] || []);

        setLoading(false);
      } catch { setPageError("Network error."); setLoading(false); }
    };
    fetchRuleAndNext();
  }, [resolvedParams, isAuthenticated, token]);

  // Handler for moving to the next rule for overview blocks
  const handleNextPageClick = async () => {
    if (!rule || !rule.next_chunk_id) return;

    if (isOverview && isAuthenticated && token) {
      setIsRedirecting(true);
      try {
        const headers: HeadersInit = {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        };

        await fetch(`${process.env.NEXT_PUBLIC_API_URL}/check/overview/read`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({ chunk_id: rule.chunk_id }),
        });
      } catch (error) {
        console.error("Error saving overview read status:", error);
      } finally {
        setIsRedirecting(false);
      }
    }

    // Navigate to the next rule page
    router.push(`/rules/${rule.next_chunk_id}`);
  };

  // Function to generate additional exercises
  const handleGenerateMoreExercises = async <T extends Exercise>(
    exerciseType: T["type"]
  ) => {
    if (!rule || !token || !isAuthenticated) return;

    let setLoadingState: (loading: boolean) => void;
    let setExercisesState: React.Dispatch<React.SetStateAction<T[]>>;

    if (exerciseType === "fill_in_the_blank") {
      setLoadingState = setLoadingMoreFill;
      setExercisesState = setDynamicFillExercises as unknown as React.Dispatch<React.SetStateAction<T[]>>;
    } else if (exerciseType === "multiple_choice") {
      setLoadingState = setLoadingMoreChoice;
      setExercisesState = setDynamicChoiceExercises as unknown as React.Dispatch<React.SetStateAction<T[]>>;
    } else {
      setLoadingState = setLoadingMoreFree;
      setExercisesState = setDynamicFreeExercises as unknown as React.Dispatch<React.SetStateAction<T[]>>;
    }

    setLoadingState(true);
    try {
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/rule/generate_additional_exercises`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
          chunk_id: rule.chunk_id,
          exercise_type: exerciseType,
          lang: "en",
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        console.error("Failed to generate additional exercises:", errorData.detail || res.statusText);
        return;
      }

      const data: { exercises: T[] } = await res.json();
      setExercisesState((prev) => {
        const newExercisesWithIds = data.exercises.map((ex) => ({
          ...ex,
          id: -(Math.floor(Math.random() * 1000000000) + 1),
        }));
        return [...prev, ...newExercisesWithIds];
      });

    } catch (error) {
      console.error("Error generating additional exercises:", error);
    } finally {
      setLoadingState(false);
    }
  };

  if (loading) return <div className="flex justify-center items-center h-screen text-slate-400 bg-[#f8fafc]">Loading...</div>;
  if (pageError) return <div className="text-center p-10 text-rose-500">{pageError}</div>;
  if (!rule) return <div className="p-10 text-center">Rule not found</div>;

  return (
    <div className="bg-[#f8fafc] min-h-screen flex flex-col">

      <Header />

      <main className="container max-w-6xl mx-auto pt-6 pb-16 px-4 sm:px-6">

          <div className="flex items-center justify-between mb-6">
            <Link href="/" passHref>
              <Button variant="ghost" className="rounded-xl hover:bg-slate-100 text-slate-600">
                <ArrowLeft className="w-4 h-4 mr-2" />
                All Topics
              </Button>
            </Link>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">

            {/* LEFT COLUMN: THEORY */}
            <section className="lg:col-span-7 space-y-6">

              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 sm:p-8">
                <h1 className="text-2xl sm:text-3xl font-black text-slate-900 mb-6 leading-tight">
                  {rule.title}
                </h1>

                <div className="prose prose-slate max-w-none text-slate-700 leading-relaxed
                  prose-headings:font-bold prose-headings:text-slate-800 prose-headings:mt-6 prose-headings:mb-3
                  prose-p:mb-4 prose-strong:text-indigo-600 prose-strong:font-semibold
                  prose-ul:list-disc prose-ul:pl-5 prose-ul:space-y-2"
                >
                  <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        table: ({ node, ...props }) => (
                          <div className="overflow-x-auto my-6 rounded-xl border border-slate-200">
                            <table className="min-w-full divide-y divide-slate-200" {...props} />
                          </div>
                        ),
                        thead: ({ node, ...props }) => (
                          <thead className="bg-slate-50" {...props} />
                        ),
                        th: ({ node, ...props }) => (
                          <th className="px-6 py-3 text-left text-xs font-bold uppercase tracking-wider text-slate-500" {...props} />
                        ),
                        tbody: ({ node, ...props }) => (
                          <tbody className="bg-white divide-y divide-slate-100" {...props} />
                        ),
                        td: ({ node, ...props }) => (
                          <td className="px-6 py-4 text-sm text-slate-700 whitespace-nowrap" {...props} />
                        ),
                      }}
                    >
                      {rule.content}
                  </ReactMarkdown>
                </div>

                {/* Forward navigation button with logic branching */}
                {rule.next_chunk_id && (
                  <div className="mt-8 pt-6 border-t border-slate-100 flex justify-end">
                    {isOverview ? (
                      <Button
                        onClick={handleNextPageClick}
                        disabled={isRedirecting}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium px-5 shadow-sm flex items-center space-x-2"
                      >
                        {isRedirecting ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <>
                            <span>Next Rule</span>
                            <ArrowRight className="w-4 h-4" />
                          </>
                        )}
                      </Button>
                    ) : (
                      <Link href={`/rules/${rule.next_chunk_id}`} passHref>
                        <Button className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium px-5 shadow-sm flex items-center space-x-2">
                          <span>Next Rule</span>
                          <ArrowRight className="w-4 h-4" />
                        </Button>
                      </Link>
                    )}
                  </div>
                )}
              </div>

              {/* Related Topics */}
              {rule.related_rules && rule.related_rules.length > 0 && (
                <Card className="border border-slate-100 bg-white shadow-sm rounded-2xl p-6">
                  <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center space-x-2">
                    <span className="w-1.5 h-3 bg-slate-300 rounded-full"></span>
                    <span>Recommended to study next:</span>
                  </h3>
                  <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {rule.related_rules.map((relatedRule) => (
                      <li key={relatedRule.chunk_id}>
                        <Link
                          href={`/rules/${relatedRule.chunk_id}`}
                          className="text-sm font-medium text-slate-600 hover:text-indigo-600 p-3 rounded-xl border border-slate-50 bg-slate-50/40 hover:bg-indigo-50/30 hover:border-indigo-100 transition-all flex items-center space-x-2 group h-full"
                        >
                          <span className="w-1.5 h-1.5 bg-slate-400 rounded-full group-hover:bg-indigo-500 transition-colors shrink-0"></span>
                          <span className="underline underline-offset-4 decoration-transparent group-hover:decoration-indigo-600 transition-all line-clamp-1">
                            {relatedRule.display_title || relatedRule.chunk_id}
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
            </section>

            {/* RIGHT COLUMN: PRACTICE */}
            <section className="lg:col-span-5 sticky top-24">
              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
                <h2 className="text-xl font-bold text-slate-800 flex items-center space-x-2 mb-4">
                  <span className="flex w-2 h-5 bg-indigo-600 rounded-full"></span>
                  <span>Practice</span>
                </h2>

              <Tabs defaultValue="fill" className="w-full">
                <TabsList className="flex w-full bg-slate-100 p-1 rounded-xl mb-6">
                  <TabsTrigger
                    value="fill"
                    className="flex-1 rounded-lg text-xs font-semibold py-2 px-1 flex items-center justify-center data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all"
                  >
                    <CheckSquare className="w-3.5 h-3.5 mr-1 text-indigo-600 shrink-0" />
                    <span className="truncate">Blanks</span>
                  </TabsTrigger>

                  <TabsTrigger
                    value="choice"
                    className="flex-1 rounded-lg text-xs font-semibold py-2 px-1 flex items-center justify-center data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all"
                  >
                    <ListPlus className="w-3.5 h-3.5 mr-1 text-emerald-600 shrink-0" />
                    <span className="truncate">Tests</span>
                  </TabsTrigger>

                  <TabsTrigger
                    value="free"
                    className="flex-1 rounded-lg text-xs font-semibold py-2 px-1 flex items-center justify-center data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all"
                  >
                    <PenTool className="w-3.5 h-3.5 mr-1 text-purple-600 shrink-0" />
                    <span className="truncate">Writing</span>
                  </TabsTrigger>
                </TabsList>

                {/* TABS CONTENT */}
                <TabsContent value="fill" className="space-y-4 focus-visible:outline-none">
                  {dynamicFillExercises.length > 0 ? (
                    <>
                      <div className="flex justify-between items-center text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                        <span>Exercise {currentFillIdx + 1} of {dynamicFillExercises.length}</span>
                        <div className="flex space-x-1">
                          <Button variant="ghost" size="icon" className="h-6 w-6 rounded-md hover:bg-slate-100" disabled={currentFillIdx === 0} onClick={() => setCurrentFillIdx(p => p - 1)}>
                            <ArrowLeft className="w-3 h-3" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-6 w-6 rounded-md hover:bg-slate-100" disabled={currentFillIdx === dynamicFillExercises.length - 1} onClick={() => setCurrentFillIdx(p => p + 1)}>
                            <ArrowRight className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                      <FillInTheBlankExerciseComponent
                        exercise={dynamicFillExercises[currentFillIdx] as FillInTheBlankExercise}
                        ruleChunkId={rule.chunk_id} isAuthenticated={isAuthenticated} token={token}
                      />
                      <Button
                        onClick={() => handleGenerateMoreExercises("fill_in_the_blank")}
                        disabled={loadingMoreFill}
                        className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-medium transition-all flex items-center justify-center space-x-2"
                      >
                        {loadingMoreFill ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PlusCircle className="mr-2 h-4 w-4" />}
                        <span>Generate 5 more blanks</span>
                      </Button>
                    </>
                  ) : (
                    <p className="text-sm text-slate-400 text-center py-4">No exercises of this type</p>
                  )}
                </TabsContent>

                <TabsContent value="choice" className="space-y-4 focus-visible:outline-none">
                  {dynamicChoiceExercises.length > 0 ? (
                    <>
                      <div className="flex justify-between items-center text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                        <span>Exercise {currentChoiceIdx + 1} of {dynamicChoiceExercises.length}</span>
                        <div className="flex space-x-1">
                          <Button variant="ghost" size="icon" className="h-6 w-6 rounded-md hover:bg-slate-100" disabled={currentChoiceIdx === 0} onClick={() => setCurrentChoiceIdx(p => p - 1)}>
                            <ArrowLeft className="w-3 h-3" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-6 w-6 rounded-md hover:bg-slate-100" disabled={currentChoiceIdx === dynamicChoiceExercises.length - 1} onClick={() => setCurrentChoiceIdx(p => p + 1)}>
                            <ArrowRight className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                      <MultipleChoiceExerciseComponent
                        exercise={dynamicChoiceExercises[currentChoiceIdx] as MultipleChoiceExercise}
                        ruleChunkId={rule.chunk_id} isAuthenticated={isAuthenticated} token={token}
                      />
                      <Button
                        onClick={() => handleGenerateMoreExercises("multiple_choice")}
                        disabled={loadingMoreChoice}
                        className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-medium transition-all flex items-center justify-center space-x-2"
                      >
                        {loadingMoreChoice ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PlusCircle className="mr-2 h-4 w-4" />}
                        <span>Generate 5 more tests</span>
                      </Button>
                    </>
                  ) : (
                    <p className="text-sm text-slate-400 text-center py-4">No exercises of this type</p>
                  )}
                </TabsContent>

                <TabsContent value="free" className="space-y-4 focus-visible:outline-none">
                  {dynamicFreeExercises.length > 0 ? (
                    <>
                      <div className="flex justify-between items-center text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                        <span>Exercise {currentFreeIdx + 1} of {dynamicFreeExercises.length}</span>
                        <div className="flex space-x-1">
                          <Button variant="ghost" size="icon" className="h-6 w-6 rounded-md hover:bg-slate-100" disabled={currentFreeIdx === 0} onClick={() => setCurrentFreeIdx(p => p - 1)}>
                            <ArrowLeft className="w-3 h-3" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-6 w-6 rounded-md hover:bg-slate-100" disabled={currentFreeIdx === dynamicFreeExercises.length - 1} onClick={() => setCurrentFreeIdx(p => p + 1)}>
                            <ArrowRight className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                      <FreeResponseExerciseComponent
                        exercise={dynamicFreeExercises[currentFreeIdx] as FreeResponseExercise}
                        ruleChunkId={rule.chunk_id} isAuthenticated={isAuthenticated} token={token}
                      />
                      <Button
                        onClick={() => handleGenerateMoreExercises("free_response")}
                        disabled={loadingMoreFree}
                        className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-medium transition-all flex items-center justify-center space-x-2"
                      >
                        {loadingMoreFree ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PlusCircle className="mr-2 h-4 w-4" />}
                        <span>Generate 5 more free responses</span>
                      </Button>
                    </>
                  ) : (
                    <p className="text-sm text-slate-400 text-center py-4">No exercises of this type</p>
                  )}
                </TabsContent>
              </Tabs>
            </div>

          </section>
        </div>
      </main>
    </div>
  );
}
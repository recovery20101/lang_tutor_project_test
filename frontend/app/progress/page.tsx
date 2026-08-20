"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/context/auth-context";
import { Header } from "@/components/ui/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  BookOpen,
  Clock,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  Headphones,
  Type,
  GraduationCap
} from "lucide-react";

// Helper for topic icons, matching the main page
const getTopicIcon = (topicName: string) => {
  const name = topicName.toLowerCase();
  if (name.includes('phonology')) return <Headphones className="w-5 h-5 text-indigo-500" />;
  if (name.includes('orthography')) return <Type className="w-5 h-5 text-amber-500" />;
  if (name.includes('noun')) return <BookOpen className="w-5 h-5 text-emerald-500" />;
  if (name.includes('article')) return <GraduationCap className="w-5 h-5 text-sky-500" />;
  return <BookOpen className="w-5 h-5 text-purple-500" />;
};

interface TopicProgress {
  name: string;
  completed_count: number;
  total_count: number;
}

interface ReviewItem {
  chunk_id: string;
  display_title: string;
  overdue_days: number;
}

interface ProgressData {
  topics: TopicProgress[];
  reviews: ReviewItem[];
}

export default function ProgressPage() {
  const { isAuthenticated, userLevel } = useAuth();
  const [data, setData] = useState<ProgressData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchProgress() {
      if (!isAuthenticated) {
        setLoading(false);
        return;
      }
      try {
        setLoading(true);
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/progress`, {
          cache: 'no-store',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
        });
        if (res.ok) {
          const progressData = await res.json();
          setData(progressData);
        } else {
          console.error("Failed to fetch progress data");
        }
      } catch (error) {
        console.error("Error fetching progress:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchProgress();
  }, [isAuthenticated, userLevel]);

  // Protection: If user is logged in as guest
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-[#f8fafc]">
        <Header />
        <div className="container mx-auto max-w-4xl py-20 px-4 text-center">
          <Card className="border-none shadow-sm rounded-2xl p-8 bg-white max-w-md mx-auto">
            <CardContent className="space-y-4 pt-6">
              <div className="p-3 bg-indigo-50 text-indigo-600 rounded-full w-12 h-12 flex items-center justify-center mx-auto">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-slate-800">Personal Progress Unavailable</h2>
              <p className="text-sm text-slate-500">
                Please log in or register so that the SM-2 algorithm can track your repetitions and calculate your learning progress.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8fafc]">
      <Header />

      <div className="container mx-auto max-w-5xl py-12 px-4 sm:px-6">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Your Progress</h1>
          <p className="text-slate-500 mt-1">
            Spaced repetition management and Spanish grammar mastery analytics.
          </p>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64 text-slate-400">Loading progress analytics...</div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">

            {/* LEFT COLUMN: Topic Progress */}
            <div className="lg:col-span-2 space-y-6">
              <Card className="border border-slate-100 bg-white shadow-sm rounded-2xl overflow-hidden">
                <CardHeader className="bg-slate-50/50 border-b border-slate-100 py-4 px-6">
                  <CardTitle className="text-lg font-bold text-slate-800 flex items-center space-x-2">
                    <CheckCircle2 className="w-5 h-5 text-indigo-600" />
                    <span>GRAMMAR LEARNING ({userLevel})</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 space-y-6">
                  {!data?.topics || data.topics.length === 0 ? (
                    <p className="text-sm text-slate-400 text-center py-4">No topic statistics available.</p>
                  ) : (
                    data.topics.map((topic) => {
                      const percentage = topic.total_count > 0
                        ? Math.round((topic.completed_count / topic.total_count) * 100)
                        : 0;

                      return (
                        <div key={topic.name} className="space-y-2">
                          <div className="flex justify-between items-center text-sm font-medium">
                            <div className="flex items-center space-x-2.5">
                              <div className="p-1.5 bg-slate-50 rounded-lg border border-slate-100">
                                {getTopicIcon(topic.name)}
                              </div>
                              <span className="text-slate-700 font-semibold tracking-wide">
                                {topic.name.replace(/_/g, ' ').toUpperCase()}
                              </span>
                            </div>
                            <span className="text-slate-500">
                              {topic.completed_count}/{topic.total_count} rules
                            </span>
                          </div>

                          <div className="flex items-center space-x-4">
                            <Progress value={percentage} className="h-2.5 bg-slate-100 [&>div]:bg-indigo-600 rounded-full flex-1" />
                            <span className="text-xs font-bold text-slate-600 min-w-[30px] text-right">
                              {percentage}%
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </CardContent>
              </Card>
            </div>

            {/* RIGHT COLUMN: SM-2 Review Queue */}
            <div className="space-y-6">
              <Card className="border border-slate-100 bg-white shadow-sm rounded-2xl overflow-hidden">
                <CardHeader className="bg-slate-50/50 border-b border-slate-100 py-4 px-5">
                  <CardTitle className="text-lg font-bold text-slate-800 flex items-center space-x-2">
                    <Clock className="w-5 h-5 text-amber-500" />
                    <span>TODAY'S REVIEWS</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-5">
                  {!data?.reviews || data.reviews.length === 0 ? (
                    <div className="text-center py-8 px-4 bg-emerald-50/40 border border-dashed border-emerald-100 rounded-xl space-y-2">
                      <Sparkles className="w-6 h-6 text-emerald-500 mx-auto" />
                      <p className="text-sm font-semibold text-emerald-800">All topics mastered!</p>
                      <p className="text-xs text-emerald-600">The SM-2 algorithm has no new cards scheduled for today.</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-xs text-slate-400 mb-2">
                        Recommended for review to maintain long-term memory:
                      </p>
                      {data.reviews.map((review) => (
                        <Link
                          key={review.chunk_id}
                          href={`/rules/${review.chunk_id}`}
                          className="flex flex-col justify-between p-3.5 bg-slate-50/50 hover:bg-indigo-50/30 border border-slate-100 hover:border-indigo-100 rounded-xl transition-all duration-200 group relative"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <span className="text-sm font-semibold text-slate-700 group-hover:text-indigo-600 transition-colors pr-4">
                              {review.display_title || review.chunk_id}
                            </span>
                            <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-indigo-500 group-hover:translate-x-0.5 transition-all shrink-0 mt-0.5" />
                          </div>

                          <div className="mt-2.5 flex items-center">
                            {review.overdue_days > 0 ? (
                              <Badge variant="outline" className="text-[11px] font-medium text-rose-600 bg-rose-50 border-rose-100 rounded-md py-0 px-1.5">
                                overdue by {review.overdue_days} {review.overdue_days === 1 ? 'day' : 'days'}
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="text-[11px] font-medium text-amber-600 bg-amber-50 border-amber-100 rounded-md py-0 px-1.5">
                                review today
                              </Badge>
                            )}
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { useAuth } from "@/context/auth-context";
import { useState, useEffect } from "react";
import { BookOpen, GraduationCap, Headphones, Type, CheckCircle2 } from "lucide-react";
import { Header } from "@/components/ui/header";

const getTopicIcon = (topicName: string) => {
  const name = topicName.toLowerCase();
  if (name.includes('phonology')) return <Headphones className="w-5 h-5 text-indigo-500" />;
  if (name.includes('orthography')) return <Type className="w-5 h-5 text-amber-500" />;
  if (name.includes('noun')) return <BookOpen className="w-5 h-5 text-emerald-500" />;
  if (name.includes('article')) return <GraduationCap className="w-5 h-5 text-sky-500" />;
  return <BookOpen className="w-5 h-5 text-purple-500" />;
};

interface RuleListItem {
  chunk_id: string;
  display_title?: string;
}

interface Subtopic {
  name: string;
  rules: RuleListItem[];
  _first_chunk_id: string;
}

interface Topic {
  name: string;
  subtopics: Subtopic[];
}

async function getTopics(isAuthenticated: boolean, userLevel: string): Promise<Topic[]> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/rule/topics`, {
    cache: 'no-store',
    headers: isAuthenticated ? { 'Authorization': `Bearer ${localStorage.getItem('token')}` } : {},
  });
  if (!res.ok) {
    console.error("Failed to fetch topics:", res.status, res.statusText);
    return [];
  }
  return res.json();
}

export default function HomePage() {
  const { isAuthenticated, userLevel } = useAuth();
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loadingTopics, setLoadingTopics] = useState(true);

  useEffect(() => {
    const fetchTopics = async () => {
      setLoadingTopics(true);
      const fetchedTopics = await getTopics(isAuthenticated, userLevel);
      setTopics(fetchedTopics);
      setLoadingTopics(false);
    };
    fetchTopics();
  }, [isAuthenticated, userLevel]);

  return (
    <div className="min-gradient bg-[#f8fafc] min-h-screen">
      <Header />

      <div className="container mx-auto max-w-6xl py-12 px-4 sm:px-6">
        {loadingTopics ? (
          <div className="flex justify-center items-center h-64 text-slate-400">Loading topics...</div>
        ) : topics.length === 0 ? (
          <Card className="w-full border-none shadow-sm rounded-2xl bg-white p-6 text-center">
            <CardContent className="pt-6">
              <p className="text-slate-500">
                It looks like there are no available topics for your current level ({userLevel || "A1"}) yet.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {topics.map((topic) => (
              <Card key={topic.name} className="border border-slate-100 bg-white shadow-sm rounded-2xl overflow-hidden hover:shadow-md transition-all duration-300 flex flex-col justify-between">
                <div>
                  <CardHeader className="bg-slate-50/50 border-b border-slate-100/80 space-y-0 py-4 px-5">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-white rounded-xl shadow-sm border border-slate-100">
                        {getTopicIcon(topic.name)}
                      </div>
                      <CardTitle className="text-lg font-bold text-slate-800 tracking-wide">
                        {topic.name.replace(/_/g, ' ').toUpperCase()}
                      </CardTitle>
                    </div>
                  </CardHeader>

                  <CardContent className="p-5">
                    <Accordion type="single" collapsible className="w-full space-y-2 border-none">
                      {topic.subtopics.map((subtopic) => (
                        <AccordionItem key={subtopic.name} value={subtopic.name} className="border border-slate-100 rounded-xl px-4 bg-slate-50/30 hover:bg-slate-50/80 transition-colors data-[state=open]:bg-white data-[state=open]:border-indigo-100">
                          <AccordionTrigger className="text-left text-sm font-semibold text-slate-700 hover:no-underline py-3">
                            <span>
                              {subtopic.name.replace(/_/g, ' ').charAt(0).toUpperCase() + subtopic.name.replace(/_/g, ' ').slice(1)}
                            </span>
                          </AccordionTrigger>
                          <AccordionContent className="pb-4 pt-1">
                            <ul className="space-y-2">
                              {subtopic.rules.map((ruleItem) => (
                                <li key={ruleItem.chunk_id}>
                                  <Link
                                    href={`/rules/${ruleItem.chunk_id}`}
                                    className="flex items-center space-x-2 text-sm text-slate-600 hover:text-indigo-600 p-1 -ml-1 rounded-md transition-colors group"
                                  >
                                    <CheckCircle2 className="w-4 h-4 text-slate-300 group-hover:text-indigo-400 transition-colors shrink-0" />
                                    <span className="underline underline-offset-4 decoration-transparent group-hover:decoration-indigo-600 transition-all">
                                      {ruleItem.display_title || ruleItem.chunk_id}
                                    </span>
                                  </Link>
                                </li>
                              ))}
                            </ul>
                          </AccordionContent>
                        </AccordionItem>
                      ))}
                    </Accordion>
                  </CardContent>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
"use client";

import { useState, useRef, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAuth } from "@/context/auth-context";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import { MessageSquare, X } from "lucide-react";

interface RuleListItem {
  chunk_id: string;
  display_title?: string;
}

interface ChatMessage {
  id: number | string;
  sender: "user" | "bot";
  text: string;
  source_rules?: RuleListItem[];
}

// Interface for feedback received from backend
interface FetchedFeedback {
  message_id: number;
  feedback_type: "positive" | "negative";
}

export function FloatingChatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const { isAuthenticated, token } = useAuth();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [messageFeedback, setMessageFeedback] = useState<Record<number | string, "positive" | "negative">>({});

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Function to toggle / open / close the chat window
  const toggleChat = () => {
    setIsOpen((prev) => {
      const nextState = !prev;
      // Clear messages and feedback when chat is closed
      if (!nextState) {
        setMessages([]);
        setMessageFeedback({});
      }
      return nextState;
    });
  };

  // Load chat history and feedback upon opening
  useEffect(() => {
    let isMounted = true;

    if (!isOpen || !isAuthenticated || !token) {
      return;
    }

    const fetchChatData = async () => {
      try {
        const [historyRes, feedbackRes] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/rule/chat_history`, {
            headers: { 'Authorization': `Bearer ${token}` },
          }),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/rule/chat_feedback_for_session`, {
            headers: { 'Authorization': `Bearer ${token}` },
          })
        ]);

        if (!isMounted) return;

        if (historyRes.ok) {
          const historyData = await historyRes.json();
          setMessages(historyData.history);
        } else {
          console.error("Failed to fetch chat history:", historyRes.status, historyRes.statusText);
          setMessages([]);
        }

        if (feedbackRes.ok) {
          const feedbackData: FetchedFeedback[] = await feedbackRes.json();
          const newFeedbackState: Record<number | string, "positive" | "negative"> = {};
          feedbackData.forEach(fb => {
            if (fb.feedback_type === "positive" || fb.feedback_type === "negative") {
              newFeedbackState[fb.message_id] = fb.feedback_type;
            }
          });
          setMessageFeedback(newFeedbackState);
        } else {
          console.error("Failed to fetch chat feedback:", feedbackRes.status, feedbackRes.statusText);
          setMessageFeedback({});
        }

      } catch (error) {
        if (isMounted) {
          console.error("Error fetching chat data:", error);
          setMessages([]);
          setMessageFeedback({});
        }
      }
    };

    fetchChatData();

    return () => {
      isMounted = false;
    };
  }, [isOpen, isAuthenticated, token]);

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSendMessage = async () => {
    if (input.trim() === "") return;

    // Generate temporary unique IDs for the UI
    const tempUserMsgId = `temp-user-${Date.now()}`;
    const tempBotMsgId = `temp-bot-${Date.now()}`;

    const userMessage: ChatMessage = { id: tempUserMsgId, sender: "user", text: input };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (isAuthenticated && token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/rule/chatbot_query`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({ query: userMessage.text, lang: "en" }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        setMessages((prevMessages) => [
          ...prevMessages,
          { id: `error-${Date.now()}`, sender: "bot", text: errorData.detail || "An error occurred while receiving the response." },
        ]);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        throw new Error("Failed to get reader for streaming response.");
      }

      let botResponseText = "";
      let botSourceRules: RuleListItem[] = [];

      // Add bot to messages array with a TEMPORARY ID
      setMessages((prevMessages) => [
        ...prevMessages,
        { id: tempBotMsgId, sender: "bot", text: "", source_rules: [] },
      ]);

      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n').filter(line => line.startsWith('data: '));

        for (const line of lines) {
          const data = JSON.parse(line.substring(6));

          if (data.type === 'text') {
            botResponseText += data.content;
            setMessages((prevMessages) =>
              prevMessages.map((msg) =>
                msg.id === tempBotMsgId ? { ...msg, text: botResponseText } : msg
              )
            );
          } else if (data.type === 'final') {
              botSourceRules = data.source_rules;

              const serverUserMsgId = data.user_message_id;
              const serverBotMsgId = data.bot_message_id;

              setMessages((prevMessages) =>
                prevMessages.map((msg) => {
                  if (msg.id === tempUserMsgId) {
                    return { ...msg, id: serverUserMsgId ?? tempUserMsgId };
                  }
                  if (msg.id === tempBotMsgId) {
                    return { ...msg, id: serverBotMsgId ?? tempBotMsgId, source_rules: botSourceRules };
                  }
                  return msg;
                })
              );
            } else if (data.type === 'error') {
            botResponseText += `\n\nError: ${data.content}`;
            setMessages((prevMessages) =>
              prevMessages.map((msg) =>
                msg.id === tempBotMsgId ? { ...msg, text: botResponseText } : msg
              )
            );
            console.error("LLM Streaming Error:", data.content);
          }
        }
      }
    } catch (error) {
      console.error("Error sending query to chatbot:", error);
      setMessages((prevMessages) => [
        ...prevMessages,
        { id: `error-catch-${Date.now()}`, sender: "bot", text: "An error occurred while sending the request." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (messageId: number | string, type: "positive" | "negative") => {
    if (!isAuthenticated || !token) {
      console.warn("Cannot send feedback: User not authenticated.");
      return;
    }

    if (typeof messageId === "string" && messageId.startsWith("temp-")) {
      console.warn("Cannot send feedback yet: Message ID is temporary.");
      return;
    }

    setMessageFeedback((prev) => ({ ...prev, [messageId]: type }));

    try {
      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/rule/chat_feedback`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({ message_id: Number(messageId), feedback_type: type }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        console.error("Failed to send feedback:", errorData.detail || res.statusText);
        setMessageFeedback((prev) => {
          const newState = { ...prev };
          delete newState[messageId];
          return newState;
        });
      } else {
        console.log(`Feedback for message ${messageId} recorded.`);
      }
    } catch (error) {
      console.error("Error sending feedback:", error);
      setMessageFeedback((prev) => {
        const newState = { ...prev };
        delete newState[messageId];
        return newState;
      });
    }
  };

  return (
    <>
      {/* Chat toggle button */}
      <Button
        className="fixed bottom-6 right-6 rounded-full w-14 h-14 shadow-2xl z-50 bg-gradient-to-br from-blue-600 to-indigo-700 hover:from-blue-700 hover:to-indigo-800"
        onClick={toggleChat}
        aria-label={isOpen ? "Close chat" : "Open chat"}
      >
        {isOpen ? <X size={24} className="text-white" /> : <MessageSquare size={24} className="text-white" />}
      </Button>

      {/* Chat window */}
      {isOpen && (
        <Card className="fixed bottom-24 right-6 w-full max-w-sm h-[60vh] flex flex-col shadow-2xl z-50 border border-gray-100 rounded-3xl overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between py-3 px-4 border-b border-gray-100 bg-gray-50/50 shrink-0">
            <CardTitle className="text-base font-semibold text-gray-900">AI Assistant</CardTitle>
            <Button variant="ghost" size="icon" onClick={toggleChat} aria-label="Close" className="text-gray-500 hover:text-gray-800 w-8 h-8">
              <X size={16} />
            </Button>
          </CardHeader>

          <CardContent className="flex-1 flex flex-col min-h-0 p-5 bg-white">
            <ScrollArea className="flex-1 h-full min-h-0 pr-3 mb-5">
              <div className="flex flex-col space-y-5 h-auto pb-2">
                {messages.length === 0 && !isAuthenticated && (
                  <div className="text-center text-gray-500 bg-gray-50 p-4 rounded-xl">
                    Please log in to save chat history.
                  </div>
                )}
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.sender === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-[85%] p-4 rounded-2xl shadow-sm ${
                        message.sender === "user"
                          ? "bg-blue-600 text-white rounded-br-lg"
                          : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100 rounded-bl-lg"
                      }`}
                    >
                      <div className="prose prose-sm prose-slate dark:prose-invert max-w-none break-words">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.text}
                        </ReactMarkdown>
                      </div>

                      {message.sender === "bot" && message.source_rules && message.source_rules.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 text-xs">
                          <p className="font-semibold text-gray-700 dark:text-gray-300 mb-1">Relevant Rules:</p>
                          <ul className="list-disc pl-4 space-y-1">
                            {message.source_rules.map((rule, idx) => (
                              <li key={idx}>
                                <Link href={`/rules/${rule.chunk_id}`} className="text-blue-600 hover:underline dark:text-blue-400 font-medium">
                                  {rule.display_title || rule.chunk_id}
                                </Link>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {message.sender === "bot" && (
                        <div className="flex space-x-1.5 mt-3 pt-2 border-t border-gray-100">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleFeedback(message.id, "positive")}
                            disabled={!!messageFeedback[message.id]}
                            className={`p-2 h-auto text-lg rounded-full hover:bg-gray-200 ${messageFeedback[message.id] === "positive" ? "bg-green-100 text-green-700" : "text-gray-400"}`}
                          >
                            👍
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleFeedback(message.id, "negative")}
                            disabled={!!messageFeedback[message.id]}
                            className={`p-2 h-auto text-lg rounded-full hover:bg-gray-200 ${messageFeedback[message.id] === "negative" ? "bg-red-100 text-red-700" : "text-gray-400"}`}
                          >
                            👎
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            <div className="flex gap-2 p-1 border border-gray-200 rounded-full bg-white shadow-inner shrink-0">
              <Input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
                placeholder="Ask a grammar question..."
                disabled={loading}
                className="flex-1 border-0 focus-visible:ring-0 focus-visible:ring-offset-0 px-4 h-10 rounded-full"
              />
              <Button onClick={handleSendMessage} disabled={loading} className="h-10 rounded-full px-5 bg-indigo-700 hover:bg-indigo-800">
                {loading ? "..." : "Send"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </>
  );
}
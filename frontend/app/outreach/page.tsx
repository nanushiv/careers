"use client";

import { useEffect, useState } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import { api } from "@/lib/api";
import {
  Mail, Copy, Check, Loader2, Plus, Trash2, Lock, Send,
  Bell, BellRing, ChevronDown, Users, RefreshCw, Linkedin,
} from "lucide-react";
import Link from "next/link";

const GOALS = [
  { value: "informational_interview", label: "Informational Interview" },
  { value: "referral_request", label: "Ask for Referral" },
  { value: "job_inquiry", label: "Direct Job Inquiry" },
  { value: "networking", label: "General Networking" },
  { value: "thank_you_post_interview", label: "Post-Interview Thank You" },
];

interface GeneratedEmail {
  subject: string;
  body: string;
  word_count: number;
  follow_up_suggestion: string;
  personalization_hooks: string[];
}

interface Recipient {
  name: string;
  title: string;
  company: string;
  context: string;
  email: string;
}

interface ContactSuggestion {
  title: string;
  company: string;
  why: string;
  goal: string;
  linkedin_keywords: string;
}

const GOAL_LABEL: Record<string, string> = {
  informational_interview: "Informational",
  referral_request: "Referral",
  job_inquiry: "Job Inquiry",
  networking: "Networking",
  thank_you_post_interview: "Thank You",
};

export default function OutreachPage() {
  const { getToken } = useAuth();
  const { user } = useUser();
  const senderEmail = user?.primaryEmailAddress?.emailAddress || "";

  const [goal, setGoal] = useState("informational_interview");
  const [recipients, setRecipients] = useState<Recipient[]>([
    { name: "", title: "", company: "", context: "", email: "" },
  ]);
  const [results, setResults] = useState<Array<{ recipient: Recipient; email: GeneratedEmail }>>([]);
  const [loading, setLoading] = useState(false);
  const [isPro, setIsPro] = useState<boolean | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [reminded, setReminded] = useState<Record<number, boolean>>({});
  const [remindingAll, setRemindingAll] = useState(false);

  // Contact suggestions
  const [suggestions, setSuggestions] = useState<ContactSuggestion[]>([]);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

  useEffect(() => {
    const checkPlan = async () => {
      const token = await getToken();
      if (!token) { setIsPro(false); return; }
      const resp = await api.getMe(token);
      const plan = resp.data?.plan || "free";
      setIsPro(plan === "pro" || plan === "team");
    };
    checkPlan();
  }, [getToken]);

  const addRecipient = () => {
    if (recipients.length >= 10) return;
    setRecipients(p => [...p, { name: "", title: "", company: "", context: "", email: "" }]);
  };

  const removeRecipient = (i: number) => {
    setRecipients(p => p.filter((_, idx) => idx !== i));
  };

  const updateRecipient = (i: number, field: keyof Recipient, value: string) => {
    setRecipients(p => p.map((r, idx) => idx === i ? { ...r, [field]: value } : r));
  };

  const generate = async () => {
    const valid = recipients.filter(r => r.name && r.company);
    if (!valid.length) return;
    setLoading(true);
    setResults([]);
    try {
      const token = await getToken();
      if (!token) return;
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/outreach/bulk-generate`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ recipients: valid, goal }),
        }
      );
      const data = await resp.json();
      if (data.success) setResults(data.data.emails);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const copyEmail = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const saveReminder = async (token: string, result: { recipient: Recipient; email: GeneratedEmail }) => {
    const match = result.email.follow_up_suggestion?.match(/(\d+)\s*day/i);
    const days = match ? parseInt(match[1]) : 5;
    await fetch(`${process.env.NEXT_PUBLIC_API_URL!}/outreach/reminders`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        recipient_name: result.recipient.name,
        company: result.recipient.company,
        goal,
        email_subject: result.email.subject,
        days_until_followup: days,
      }),
    });
  };

  const setReminder = async (i: number, result: { recipient: Recipient; email: GeneratedEmail }) => {
    const token = await getToken();
    if (!token) return;
    await saveReminder(token, result);
    setReminded(p => ({ ...p, [i]: true }));
  };

  const setRemindersForAll = async () => {
    const token = await getToken();
    if (!token || remindingAll) return;
    setRemindingAll(true);
    try {
      await Promise.all(results.map(r => saveReminder(token, r)));
      setReminded(Object.fromEntries(results.map((_, i) => [i, true])));
    } finally {
      setRemindingAll(false);
    }
  };

  const loadSuggestions = async () => {
    // Use cached results if already loaded
    if (suggestions.length > 0) { setSuggestionsOpen(true); return; }
    setLoadingSuggestions(true);
    setSuggestionsOpen(true);
    try {
      const token = await getToken();
      if (!token) return;
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL!}/outreach/contact-suggestions`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await resp.json();
      if (data.success) setSuggestions(data.data.contacts || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const refreshSuggestions = async () => {
    setSuggestions([]);
    setLoadingSuggestions(true);
    setSuggestionsOpen(true);
    try {
      const token = await getToken();
      if (!token) return;
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL!}/outreach/contact-suggestions`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await resp.json();
      if (data.success) setSuggestions(data.data.contacts || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const pickContact = (s: ContactSuggestion) => {
    // Fill the first empty recipient slot, or replace first slot
    const firstEmpty = recipients.findIndex(r => !r.name && !r.company);
    const idx = firstEmpty >= 0 ? firstEmpty : 0;
    setRecipients(p =>
      p.map((r, i) =>
        i === idx ? { ...r, title: s.title, company: s.company, context: s.why } : r
      )
    );
    setGoal(s.goal);
    setSuggestionsOpen(false);
  };

  if (isPro === null) return (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="w-6 h-6 text-violet-400 animate-spin" />
    </div>
  );
  if (!isPro) return <ProGate />;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Mail className="w-6 h-6 text-violet-400" /> Outreach Drafter
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Personalized cold emails — AI-written, you send. Never auto-sends.
          </p>
        </div>
        {senderEmail && (
          <div className="flex items-center gap-2 px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg">
            <div className="w-2 h-2 rounded-full bg-green-400 shrink-0" />
            <div className="text-right">
              <p className="text-xs text-gray-500">Sending from</p>
              <p className="text-xs font-medium text-gray-200">{senderEmail}</p>
            </div>
            <Link href="/settings"
              className="ml-1 text-xs text-violet-400 hover:text-violet-300 border-l border-gray-700 pl-2">
              change
            </Link>
          </div>
        )}
      </div>

      {/* Who to reach out to — collapsible AI suggestions */}
      <div className="mb-6 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <button
          onClick={() => suggestionsOpen ? setSuggestionsOpen(false) : loadSuggestions()}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-800/40 transition-colors text-left">
          <div className="flex items-center gap-2.5">
            <Users className="w-4 h-4 text-violet-400 shrink-0" />
            <span className="text-sm font-medium text-gray-200">Who to reach out to</span>
            <span className="text-xs text-gray-500 hidden sm:inline">
              — AI-suggested contacts based on your resume &amp; target roles
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {loadingSuggestions && <Loader2 className="w-3.5 h-3.5 text-violet-400 animate-spin" />}
            <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${suggestionsOpen ? "rotate-180" : ""}`} />
          </div>
        </button>

        {suggestionsOpen && (
          <div className="border-t border-gray-800 p-5">
            {loadingSuggestions ? (
              <div className="flex items-center justify-center py-8 gap-2">
                <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />
                <span className="text-sm text-gray-400">Analyzing your profile...</span>
              </div>
            ) : suggestions.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-6">Could not generate suggestions. Try refreshing.</p>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
                  {suggestions.map((s, i) => (
                    <div key={i}
                      className="p-3.5 bg-gray-800/60 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors flex flex-col">
                      <div className="mb-2">
                        <div className="flex items-start justify-between gap-1 mb-0.5">
                          <p className="text-sm font-semibold text-gray-100 leading-tight">{s.title}</p>
                          <span className="shrink-0 text-xs px-1.5 py-0.5 bg-violet-500/15 text-violet-400 rounded border border-violet-500/20">
                            {GOAL_LABEL[s.goal] || s.goal}
                          </span>
                        </div>
                        <p className="text-xs text-violet-400 font-medium">{s.company}</p>
                      </div>
                      <p className="text-xs text-gray-400 leading-relaxed flex-1 mb-3">{s.why}</p>
                      <div className="flex items-center gap-2">
                        <a
                          href={`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(s.linkedin_keywords)}`}
                          target="_blank" rel="noopener noreferrer"
                          className="flex items-center gap-1 px-2 py-1.5 text-xs text-blue-400 hover:text-blue-300 bg-blue-500/10 border border-blue-500/20 rounded-lg transition-colors">
                          <Linkedin className="w-3 h-3" /> Find
                        </a>
                        <button
                          onClick={() => pickContact(s)}
                          className="flex items-center gap-1 px-2 py-1.5 text-xs text-violet-300 hover:text-violet-200 bg-violet-500/10 border border-violet-500/20 rounded-lg transition-colors ml-auto">
                          Use this →
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex justify-end">
                  <button
                    onClick={refreshSuggestions}
                    disabled={loadingSuggestions}
                    className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40">
                    <RefreshCw className="w-3 h-3" /> Refresh suggestions
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Input */}
        <div className="space-y-4">
          {/* Goal selector */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-sm font-medium text-gray-300 mb-3">Outreach goal</p>
            <div className="space-y-2">
              {GOALS.map(g => (
                <button key={g.value} onClick={() => setGoal(g.value)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm border transition-all ${
                    goal === g.value
                      ? "bg-violet-600/20 border-violet-500/40 text-violet-200"
                      : "bg-gray-800/60 border-gray-700 text-gray-300 hover:border-gray-600"
                  }`}>
                  {goal === g.value ? "● " : "○ "}{g.label}
                </button>
              ))}
            </div>
          </div>

          {/* Recipients */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm font-medium text-gray-300">Recipients ({recipients.length}/10)</p>
              <button onClick={addRecipient} disabled={recipients.length >= 10}
                className="flex items-center gap-1 text-xs font-medium text-violet-400 hover:text-violet-300 disabled:opacity-40 px-2 py-1 rounded-lg hover:bg-violet-500/10 transition-colors">
                <Plus className="w-3 h-3" /> Add recipient
              </button>
            </div>
            <p className="text-xs text-gray-600 mb-3">Each recipient gets a unique, personalized email in one click.</p>

            <div className="space-y-4">
              {recipients.map((r, i) => (
                <div key={i} className="p-3 bg-gray-800/50 rounded-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-gray-500 font-medium">Recipient {i + 1}</p>
                    {recipients.length > 1 && (
                      <button onClick={() => removeRecipient(i)} className="text-gray-600 hover:text-red-400">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <input value={r.name} onChange={e => updateRecipient(i, "name", e.target.value)}
                      placeholder="Full name *" className={inp} />
                    <input value={r.title} onChange={e => updateRecipient(i, "title", e.target.value)}
                      placeholder="Job title" className={inp} />
                    <input value={r.company} onChange={e => updateRecipient(i, "company", e.target.value)}
                      placeholder="Company *" className={inp} />
                    <input value={r.email} onChange={e => updateRecipient(i, "email", e.target.value)}
                      placeholder="Their email (for sending)" type="email" className={inp} />
                  </div>
                  <input value={r.context} onChange={e => updateRecipient(i, "context", e.target.value)}
                    placeholder="Context — e.g. 'hiring PMs', 'met at conference'" className={inp} />
                </div>
              ))}
            </div>

            <button onClick={generate}
              disabled={loading || !recipients.some(r => r.name && r.company)}
              className="w-full mt-4 flex items-center justify-center gap-2 py-3 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white text-sm font-semibold rounded-xl transition-colors">
              {loading
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</>
                : <><Mail className="w-4 h-4" /> Generate {recipients.filter(r => r.name && r.company).length} Email(s)</>}
            </button>
          </div>
        </div>

        {/* Right: Results */}
        <div className="space-y-4">
          {results.length > 1 && (
            <div className="flex items-center justify-between px-4 py-2.5 bg-gray-900 border border-gray-800 rounded-xl">
              <p className="text-xs text-gray-400">{results.length} emails generated</p>
              <button
                onClick={setRemindersForAll}
                disabled={remindingAll || results.every((_, i) => reminded[i])}
                className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border transition-colors ${
                  results.every((_, i) => reminded[i])
                    ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                    : "border-gray-700 text-gray-400 hover:border-amber-500/50 hover:text-amber-300 hover:bg-amber-500/5"
                }`}>
                {remindingAll
                  ? <><Loader2 className="w-3 h-3 animate-spin" /> Setting...</>
                  : results.every((_, i) => reminded[i])
                    ? <><BellRing className="w-3 h-3" /> All reminders set</>
                    : <><BellRing className="w-3 h-3" /> Set reminders for all</>}
              </button>
            </div>
          )}

          {results.length === 0 && !loading ? (
            <div className="h-full min-h-64 bg-gray-900 border border-gray-800 border-dashed rounded-xl flex items-center justify-center">
              <div className="text-center p-8">
                <Mail className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                <p className="text-sm text-gray-500">
                  Add recipients and click Generate — each person gets their own personalized email.
                </p>
              </div>
            </div>
          ) : (
            results.map((result, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-100">{result.recipient.name}</p>
                    <p className="text-xs text-gray-400">{result.recipient.title} · {result.recipient.company}</p>
                    {result.recipient.email && (
                      <p className="text-xs text-gray-500 mt-0.5">{result.recipient.email}</p>
                    )}
                  </div>
                  <span className="text-xs text-gray-500">{result.email.word_count} words</span>
                </div>

                <div className="mb-3 p-2 bg-gray-800 rounded-lg">
                  <p className="text-xs text-gray-500 mb-0.5">Subject</p>
                  <p className="text-sm text-gray-200 font-medium">{result.email.subject}</p>
                </div>

                <div className="p-3 bg-gray-800/60 rounded-lg mb-3">
                  <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
                    {result.email.body}
                  </p>
                </div>

                {result.email.follow_up_suggestion && (
                  <div className="flex items-start gap-2 mb-3 p-2.5 bg-violet-500/5 border border-violet-500/20 rounded-lg">
                    <Bell className="w-3.5 h-3.5 text-violet-400 mt-0.5 shrink-0" />
                    <p className="text-xs text-violet-300 leading-relaxed">{result.email.follow_up_suggestion}</p>
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => copyEmail(`${i}`, `Subject: ${result.email.subject}\n\n${result.email.body}`)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium rounded-lg border border-gray-700 transition-colors">
                    {copied === `${i}`
                      ? <><Check className="w-3 h-3 text-green-400" /> Copied!</>
                      : <><Copy className="w-3 h-3" /> Copy</>}
                  </button>
                  <a
                    href={result.recipient.email
                      ? `https://mail.google.com/mail/?view=cm&to=${encodeURIComponent(result.recipient.email)}&su=${encodeURIComponent(result.email.subject)}&body=${encodeURIComponent(result.email.body)}`
                      : "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                      result.recipient.email
                        ? "bg-violet-600 hover:bg-violet-500 text-white"
                        : "bg-gray-700 text-gray-400 border border-gray-600 cursor-not-allowed"
                    }`}
                    title={result.recipient.email ? undefined : "Add their email address to enable sending"}
                    onClick={e => { if (!result.recipient.email) e.preventDefault(); }}>
                    <Send className="w-3 h-3" />
                    {result.recipient.email ? "Open in Gmail" : "Add email to send"}
                  </a>
                  <button
                    onClick={() => setReminder(i, result)}
                    disabled={reminded[i]}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ml-auto ${
                      reminded[i]
                        ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                        : "border-gray-700 text-gray-400 hover:border-amber-500/50 hover:text-amber-300 hover:bg-amber-500/5"
                    }`}>
                    {reminded[i]
                      ? <><BellRing className="w-3 h-3" /> Reminder set</>
                      : <><Bell className="w-3 h-3" /> Remind me to follow up</>}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function ProGate() {
  return (
    <div className="max-w-4xl mx-auto text-center py-20 bg-gray-900 border border-gray-800 rounded-2xl">
      <Lock className="w-10 h-10 text-violet-400 mx-auto mb-4" />
      <h2 className="text-xl font-bold text-white mb-2">Pro Feature</h2>
      <p className="text-gray-400 max-w-sm mx-auto mb-6">
        Generate personalized cold emails to recruiters and hiring managers. AI-written, you send.
      </p>
      <Link href="/pricing"
        className="inline-flex items-center gap-2 px-6 py-3 bg-violet-600 hover:bg-violet-500 text-white font-semibold rounded-xl transition-colors">
        Upgrade to Pro
      </Link>
    </div>
  );
}

const inp = "w-full px-2.5 py-2 bg-gray-700 border border-gray-600 rounded-lg text-xs text-gray-200 placeholder:text-gray-500 focus:outline-none focus:border-violet-500 transition-colors";

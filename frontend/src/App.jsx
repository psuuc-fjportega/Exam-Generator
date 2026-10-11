import React, { useState, useEffect } from "react";
import GenerateExamForm from "./components/GenerateExamForm";
import {
  GraduationCap,
  UserCheck,
  LogIn,
  LogOut,
  Sparkles,
  FileCheck2,
  Check,
  Clock,
  Award,
  Layers,
  ChevronDown,
  ChevronUp,
  Key,
  AlertCircle,
  ExternalLink,
} from "lucide-react";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("access_token") || "");
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [generatedExamData, setGeneratedExamData] = useState(null);
  const [expandedQuestions, setExpandedQuestions] = useState({});

  // AI API Key configuration state
  const [aiStatus, setAiStatus] = useState({
    ai_configured: true,
    model_name: "gemini-3.5-flash-lite",
    key_preview: null,
    message: "",
  });
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [inputKey, setInputKey] = useState("");
  const [keyUpdating, setKeyUpdating] = useState(false);
  const [keyError, setKeyError] = useState("");
  const [keySuccess, setKeySuccess] = useState("");

  // Login form state
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [email, setEmail] = useState("teacher@example.com");
  const [password, setPassword] = useState("teacher1234");
  const [loginError, setLoginError] = useState("");

  const fetchAiStatus = async () => {
    try {
      const res = await fetch("/api/system/ai-status");
      if (res.ok) {
        const data = await res.json();
        setAiStatus(data);
      }
    } catch (err) {
      console.warn("Could not fetch AI status:", err);
    }
  };

  useEffect(() => {
    fetchAiStatus();
  }, []);

  const handleSaveKey = async (e) => {
    e.preventDefault();
    setKeyError("");
    setKeySuccess("");

    if (!inputKey.trim()) {
      setKeyError("Please enter your Gemini API key.");
      return;
    }

    const activeToken = token || localStorage.getItem("access_token");
    if (!activeToken) {
      setKeyError("Please log in as a teacher before configuring the API key.");
      return;
    }

    setKeyUpdating(true);
    try {
      const res = await fetch("/api/system/configure-key", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${activeToken}`,
        },
        body: JSON.stringify({ api_key: inputKey.trim() }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to configure Gemini API key.");
      }

      setKeySuccess("Gemini API key configured successfully!");
      setInputKey("");
      await fetchAiStatus();
      setTimeout(() => {
        setShowKeyModal(false);
        setKeySuccess("");
      }, 1200);
    } catch (err) {
      setKeyError(err.message || "Failed to configure key.");
    } finally {
      setKeyUpdating(false);
    }
  };

  const checkCurrentUser = async (authToken) => {
    if (!authToken) {
      setCurrentUser(null);
      return;
    }
    try {
      const res = await fetch("/api/users/me", {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        const user = await res.json();
        setCurrentUser(user);
      } else {
        // Token expired or invalid
        localStorage.removeItem("access_token");
        setToken("");
        setCurrentUser(null);
      }
    } catch {
      // Offline / server not running
    }
  };

  useEffect(() => {
    if (token) {
      checkCurrentUser(token);
    }
  }, [token]);

  // Quick teacher login helper to make testing instantaneous
  const handleQuickTeacherLogin = async (e) => {
    if (e) e.preventDefault();
    setAuthLoading(true);
    setLoginError("");

    try {
      // First try to login
      let loginRes = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username: email, password: password }),
      });

      // If user doesn't exist, register first
      if (loginRes.status === 400 || loginRes.status === 401 || loginRes.status === 404) {
        await fetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email,
            password: password,
            first_name: "Instructor",
            last_name: "Demo",
            role: "teacher",
          }),
        });

        // Retry login
        loginRes = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ username: email, password: password }),
        });
      }

      if (!loginRes.ok) {
        const err = await loginRes.json();
        throw new Error(err.detail || "Authentication failed");
      }

      const data = await loginRes.json();
      localStorage.setItem("access_token", data.access_token);
      setToken(data.access_token);
      setShowLoginModal(false);
      await checkCurrentUser(data.access_token);
    } catch (err) {
      setLoginError(err.message || "Failed to log in");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    setToken("");
    setCurrentUser(null);
  };

  const toggleQuestion = (index) => {
    setExpandedQuestions((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-20">
      {/* Top Navbar */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40 shadow-xs">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-slate-900 text-white p-2 rounded-lg">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-lg leading-tight text-slate-900">
                ExamGen AI
              </h1>
              <p className="text-xs text-slate-500">
                Intelligent Examination & Blueprint System
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* AI Key Status Button */}
            <button
              onClick={() => setShowKeyModal(true)}
              className={`text-xs px-3 py-1.5 rounded-full font-medium flex items-center gap-1.5 transition-colors cursor-pointer border ${
                aiStatus.ai_configured
                  ? "bg-emerald-50 border-emerald-200 text-emerald-800 hover:bg-emerald-100"
                  : "bg-amber-50 border-amber-300 text-amber-900 hover:bg-amber-100 animate-pulse"
              }`}
              title="Click to view or configure Gemini API Key"
            >
              {aiStatus.ai_configured ? (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                  <span>AI Ready ({aiStatus.model_name})</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                  <span className="font-bold">AI Key Missing</span>
                </>
              )}
            </button>

            {currentUser ? (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 bg-slate-100 py-1.5 px-3 rounded-full text-xs font-medium text-slate-700">
                  <UserCheck className="w-4 h-4 text-emerald-600" />
                  <span>
                    {currentUser.first_name} {currentUser.last_name} ({currentUser.role})
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="text-xs text-slate-600 hover:text-red-600 flex items-center gap-1 font-semibold p-1.5 rounded transition-colors"
                >
                  <LogOut className="w-4 h-4" /> Sign Out
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowLoginModal(true)}
                className="bg-slate-900 hover:bg-black text-white px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-colors cursor-pointer"
              >
                <LogIn className="w-4 h-4" /> Teacher Login
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Gemini API Key Configuration Modal */}
      {showKeyModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 max-w-md w-full p-6 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="bg-slate-900 text-white p-1.5 rounded-lg">
                  <Key className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-lg text-slate-900">
                  Gemini API Configuration
                </h3>
              </div>
              <button
                onClick={() => setShowKeyModal(false)}
                className="text-gray-400 hover:text-gray-600 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-500 mb-4 leading-relaxed">
              Google Gemini is used to extract key topics, build blueprints, and generate exam questions.
              You can get a free API key from{" "}
              <a
                href="https://aistudio.google.com/apikey"
                target="_blank"
                rel="noreferrer"
                className="text-blue-600 hover:underline inline-flex items-center gap-0.5"
              >
                Google AI Studio <ExternalLink className="w-3 h-3" />
              </a>.
            </p>

            {aiStatus.ai_configured && (
              <div className="p-3 mb-4 text-xs bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg flex items-center justify-between">
                <div>
                  <span className="font-semibold">Current Status:</span> Configured & Active
                  {aiStatus.key_preview && (
                    <div className="text-slate-500 mt-0.5">Key: {aiStatus.key_preview}</div>
                  )}
                </div>
                <span className="text-xs bg-emerald-100 text-emerald-900 font-bold px-2 py-0.5 rounded">Active</span>
              </div>
            )}

            {keyError && (
              <div className="p-3 mb-4 text-xs bg-red-50 text-red-700 border border-red-200 rounded-lg">
                {keyError}
              </div>
            )}

            {keySuccess && (
              <div className="p-3 mb-4 text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg">
                {keySuccess}
              </div>
            )}

            <form onSubmit={handleSaveKey} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-700 mb-1">
                  Gemini API Key
                </label>
                <input
                  type="password"
                  value={inputKey}
                  onChange={(e) => setInputKey(e.target.value)}
                  placeholder="Paste your Gemini API key (e.g., AIzaSy...)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>

              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setShowKeyModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-slate-600 hover:bg-slate-50 font-medium cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={keyUpdating}
                  className="px-4 py-2 bg-slate-900 hover:bg-black text-white text-sm font-semibold rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                >
                  {keyUpdating ? "Validating & Saving..." : "Save & Activate Key"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Login Modal */}
      {showLoginModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 max-w-sm w-full p-6 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg text-slate-900">Teacher Authentication</h3>
              <button
                onClick={() => setShowLoginModal(false)}
                className="text-gray-400 hover:text-gray-600 cursor-pointer"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Sign in with a teacher account to upload materials and generate examinations.
            </p>

            {loginError && (
              <div className="p-3 mb-4 text-xs bg-red-50 text-red-700 border border-red-200 rounded-lg">
                {loginError}
              </div>
            )}

            <form onSubmit={handleQuickTeacherLogin} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-700 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-2.5 bg-slate-900 hover:bg-black text-white text-sm font-semibold rounded-lg transition-colors cursor-pointer disabled:opacity-50 mt-2"
              >
                {authLoading ? "Authenticating..." : "Sign In / Auto-Register"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Main Body */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-8 space-y-10">
        {!currentUser && (
          <div className="max-w-4xl mx-auto bg-amber-50 border border-amber-200 p-4 rounded-xl flex items-center justify-between text-amber-900">
            <div className="flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-amber-600 shrink-0" />
              <div className="text-sm">
                <span className="font-semibold">Teacher credentials required:</span> Log in to upload materials and generate AI exams.
              </div>
            </div>
            <button
              onClick={() => handleQuickTeacherLogin()}
              disabled={authLoading}
              className="px-3.5 py-1.5 bg-amber-900 hover:bg-black text-white rounded-lg text-xs font-semibold transition-colors cursor-pointer shrink-0"
            >
              {authLoading ? "Logging in..." : "1-Click Demo Teacher Login"}
            </button>
          </div>
        )}

        {/* Generate Exam Form */}
        <GenerateExamForm
          token={token}
          aiStatus={aiStatus}
          onOpenKeyModal={() => setShowKeyModal(true)}
          onExamGenerated={(data) => {
            setGeneratedExamData(data);
            window.scrollTo({ top: 600, behavior: "smooth" });
          }}
        />

        {/* Generated Exam Results Section */}
        {generatedExamData && (
          <div className="max-w-4xl mx-auto bg-white border border-gray-200 shadow-sm rounded-xl p-8 space-y-6 animate-in fade-in slide-in-from-bottom-4">
            <div className="border-b border-gray-100 pb-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                    Generated Successfully
                  </span>
                  <span className="text-xs text-slate-400">
                    Exam #{generatedExamData.examination?.id}
                  </span>
                </div>
                <h3 className="text-2xl font-bold text-slate-900">
                  {generatedExamData.examination?.title}
                </h3>
              </div>
              <button
                onClick={() => window.print()}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors flex items-center gap-2 cursor-pointer"
              >
                <FileCheck2 className="w-4 h-4 text-slate-600" /> Print / Export
              </button>
            </div>

            {/* Exam Meta Specs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-slate-50 p-4 rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-sm text-slate-700">
                <Layers className="w-4 h-4 text-slate-500" />
                <span>
                  <strong>{generatedExamData.generation?.questions_generated || 0}</strong> Questions
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-700">
                <Clock className="w-4 h-4 text-slate-500" />
                <span>
                  <strong>{generatedExamData.examination?.time_limit_minutes}</strong> Mins
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-700">
                <Award className="w-4 h-4 text-slate-500" />
                <span>
                  Passing: <strong>{generatedExamData.examination?.passing_score}%</strong>
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-700">
                <FileCheck2 className="w-4 h-4 text-slate-500" />
                <span>
                  Status: <strong className="capitalize">{generatedExamData.examination?.status}</strong>
                </span>
              </div>
            </div>

            {/* Questions List */}
            <div className="space-y-4 pt-2">
              <h4 className="font-bold text-lg text-slate-900">Exam Questions</h4>

              {generatedExamData.generation?.questions?.length > 0 ? (
                generatedExamData.generation.questions.map((q, idx) => {
                  const isExpanded = expandedQuestions[idx] ?? true;
                  return (
                    <div
                      key={q.id || idx}
                      className="border border-gray-200 rounded-lg overflow-hidden bg-white shadow-2xs"
                    >
                      <div
                        onClick={() => toggleQuestion(idx)}
                        className="p-4 bg-slate-50 hover:bg-slate-100/80 transition-colors cursor-pointer flex items-start justify-between gap-4"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900 text-sm">
                              Q{idx + 1}.
                            </span>
                            <span className="text-xs uppercase font-bold px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                              {q.question_type?.replace("_", " ")}
                            </span>
                            <span className="text-xs uppercase font-medium px-2 py-0.5 rounded bg-blue-100 text-blue-800">
                              {q.difficulty}
                            </span>
                            {typeof q.validation_confidence === "number" && q.validation_confidence > 0 ? (
                              <span className="text-xs font-medium px-2 py-0.5 rounded bg-emerald-50 text-emerald-700">
                                Confidence: {Math.round(q.validation_confidence * 100)}%
                              </span>
                            ) : null}
                          </div>
                          <p className="font-medium text-slate-900 pt-1">
                            {q.question_text}
                          </p>
                        </div>
                        <button className="text-slate-400 hover:text-slate-600 mt-1">
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </div>

                      {isExpanded && (
                        <div className="p-4 space-y-3 border-t border-gray-200">
                          {/* Choices if any */}
                          {q.choices && q.choices.length > 0 && (
                            <div className="space-y-2">
                              <p className="text-xs font-bold uppercase text-slate-500">Choices</p>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                {q.choices.map((c, cIdx) => (
                                  <div
                                    key={cIdx}
                                    className={`p-2.5 rounded-lg text-sm border flex items-center justify-between ${
                                      c.is_correct
                                        ? "bg-emerald-50 border-emerald-300 text-emerald-900 font-medium"
                                        : "bg-white border-gray-200 text-slate-700"
                                    }`}
                                  >
                                    <span>{c.choice_text || c.text}</span>
                                    {c.is_correct && (
                                      <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Explanation */}
                          {q.explanation && (
                            <div className="text-xs bg-slate-50 p-3 rounded-lg border border-slate-200 text-slate-700">
                              <strong>Explanation: </strong> {q.explanation}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <p className="text-sm text-slate-500 italic">No questions details returned.</p>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

import React, { useState, useEffect } from "react";
import {
  UploadCloud,
  FileText,
  Loader2,
  ChevronRight,
  X,
  AlertCircle,
  CheckCircle2,
  PlusCircle,
  BookOpen,
  Sparkles,
  BarChart3,
  Target,
  Brain,
  Clock,
  ListChecks,
  ArrowLeft,
  Key,
} from "lucide-react";

export default function GenerateExamForm({
  onExamGenerated,
  token: propToken,
  aiStatus,
  onOpenKeyModal,
}) {
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Analysis result from the backend
  const [analysisResult, setAnalysisResult] = useState(null);
  const [materialId, setMaterialId] = useState(null);

  // Subjects state
  const [subjects, setSubjects] = useState([]);
  const [loadingSubjects, setLoadingSubjects] = useState(false);
  const [showNewSubjectModal, setShowNewSubjectModal] = useState(false);
  const [newSubjectName, setNewSubjectName] = useState("");
  const [newSubjectCode, setNewSubjectCode] = useState("");
  const [creatingSubject, setCreatingSubject] = useState(false);

  // Form State — starts mostly empty; populated after analysis
  const [formData, setFormData] = useState({
    subject_id: "",
    exam_title: "",
    exam_type: "all",
    total_questions: "10",
    difficulty: "medium",
    time_limit_minutes: "60",
    passing_score: "50",
    exam_description: "",
  });

  // Track which step the user is on: "upload" or "configure"
  const [step, setStep] = useState("upload");

  const getActiveToken = () => {
    return propToken || localStorage.getItem("access_token") || "";
  };

  const fetchSubjects = async () => {
    const token = getActiveToken();
    if (!token) return;

    setLoadingSubjects(true);
    try {
      const res = await fetch("/api/subjects", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setSubjects(data);
        if (data.length > 0 && !formData.subject_id) {
          setFormData((prev) => ({ ...prev, subject_id: String(data[0].id) }));
        }
      }
    } catch (err) {
      console.error("Failed to load subjects:", err);
    } finally {
      setLoadingSubjects(false);
    }
  };

  useEffect(() => {
    fetchSubjects();
  }, [propToken]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleCreateSubject = async (e) => {
    e.preventDefault();
    const token = getActiveToken();
    if (!token) {
      alert("Please log in as a teacher first.");
      return;
    }
    if (!newSubjectName.trim() || !newSubjectCode.trim()) {
      alert("Please enter subject name and code.");
      return;
    }

    setCreatingSubject(true);
    try {
      const res = await fetch("/api/subjects", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: newSubjectName.trim(),
          code: newSubjectCode.trim().toUpperCase(),
          description: "Created from exam generator",
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to create subject");
      }

      const created = await res.json();
      setSubjects((prev) => [...prev, created]);
      setFormData((prev) => ({ ...prev, subject_id: String(created.id) }));
      setShowNewSubjectModal(false);
      setNewSubjectName("");
      setNewSubjectCode("");
    } catch (err) {
      alert(err.message);
    } finally {
      setCreatingSubject(false);
    }
  };

  // ——— Step 1: Analyze the uploaded file ———
  const handleAnalyze = async (e) => {
    e.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");

    const token = getActiveToken();
    if (!token) {
      setErrorMessage("You must be logged in as a teacher. Please sign in first.");
      return;
    }
    if (aiStatus && !aiStatus.ai_configured) {
      setErrorMessage(
        "Gemini API key is not configured. Please click 'Configure Key' above to activate AI generation."
      );
      if (onOpenKeyModal) onOpenKeyModal();
      return;
    }
    if (!file) {
      setErrorMessage("Please upload a source material file (TXT, PDF, or DOCX).");
      return;
    }
    if (!formData.subject_id) {
      setErrorMessage("Please select or create a subject first.");
      return;
    }

    setIsAnalyzing(true);

    const payload = new FormData();
    payload.append("subject_id", formData.subject_id);
    payload.append("file", file);

    try {
      const response = await fetch("/api/materials/analyze", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: payload,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || (typeof data === "string" ? data : "File analysis failed")
        );
      }

      const analysis = data.analysis;
      setAnalysisResult(analysis);
      setMaterialId(data.material?.id);

      // Auto-fill the form with AI recommendations
      const dist = analysis.recommended_distribution || {};
      // Determine best exam_type from distribution
      let bestType = "all";
      const typeEntries = Object.entries(dist).filter(([, v]) => v > 0);
      if (typeEntries.length === 1) {
        bestType = typeEntries[0][0];
      }

      setFormData((prev) => ({
        ...prev,
        exam_title: analysis.title_suggestion || prev.exam_title,
        exam_description: analysis.summary || prev.exam_description,
        total_questions: String(analysis.recommended_total_questions || 10),
        difficulty: analysis.estimated_difficulty || "medium",
        time_limit_minutes: String(analysis.recommended_time_minutes || 60),
        exam_type: bestType,
      }));

      setStep("configure");
    } catch (error) {
      console.error(error);
      setErrorMessage(error.message || "Failed to analyze file.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // ——— Step 2: Generate exam from the already-analyzed material ———
  const handleGenerate = async (e) => {
    e.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");

    const token = getActiveToken();
    if (!token) {
      setErrorMessage("You must be logged in as a teacher.");
      return;
    }

    if (aiStatus && !aiStatus.ai_configured) {
      setErrorMessage(
        "Gemini API key is not configured. Please click 'Configure Key' above to activate AI generation."
      );
      if (onOpenKeyModal) onOpenKeyModal();
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch("/api/examinations/generate-from-material", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          material_id: materialId,
          exam_title: formData.exam_title,
          exam_description: formData.exam_description,
          exam_type: formData.exam_type,
          total_questions: parseInt(formData.total_questions, 10),
          difficulty: formData.difficulty,
          time_limit_minutes: parseInt(formData.time_limit_minutes, 10),
          passing_score: parseInt(formData.passing_score, 10),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || (typeof data === "string" ? data : "Examination generation failed")
        );
      }

      setSuccessMessage(
        `Exam "${data.examination?.title || formData.exam_title}" generated successfully with ${
          data.generation?.questions_generated || 0
        } questions!`
      );

      if (onExamGenerated) {
        onExamGenerated(data);
      }
    } catch (error) {
      console.error(error);
      setErrorMessage(error.message || "Failed to generate examination.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // ——— Go back to step 1 ———
  const handleBackToUpload = () => {
    setStep("upload");
    setAnalysisResult(null);
    setMaterialId(null);
    setErrorMessage("");
    setSuccessMessage("");
  };

  // ——— Render: Step 1 — Upload & Analyze ———
  const renderUploadStep = () => (
    <form onSubmit={handleAnalyze} className="space-y-8">
      {/* AI Key Missing Alert */}
      {aiStatus && !aiStatus.ai_configured && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-amber-900 shadow-xs">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
            <div className="text-sm">
              <span className="font-bold">Gemini API Key Required:</span>
              <p className="text-amber-800 text-xs mt-0.5">
                AI document analysis and examination generation require a Google Gemini API key.
              </p>
            </div>
          </div>
          {onOpenKeyModal && (
            <button
              type="button"
              onClick={onOpenKeyModal}
              className="px-3.5 py-1.5 bg-amber-900 hover:bg-black text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shrink-0 self-start sm:self-center"
            >
              <Key className="w-3.5 h-3.5" /> Configure Key
            </button>
          )}
        </div>
      )}

      {/* Subject Selection & Creation */}
      <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-bold uppercase tracking-wide text-slate-700 flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-slate-600" /> Subject
          </label>
          <button
            type="button"
            onClick={() => setShowNewSubjectModal(true)}
            className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1"
          >
            <PlusCircle className="w-3.5 h-3.5" /> Add Subject
          </button>
        </div>

        {subjects.length > 0 ? (
          <select
            required
            name="subject_id"
            value={formData.subject_id}
            onChange={handleInputChange}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
          >
            <option value="" disabled>
              -- Select a Subject --
            </option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.code})
              </option>
            ))}
          </select>
        ) : (
          <div className="flex items-center justify-between text-sm text-slate-600 py-1">
            <span>{loadingSubjects ? "Loading subjects..." : "No subjects found for your account."}</span>
            <button
              type="button"
              onClick={() => setShowNewSubjectModal(true)}
              className="px-3 py-1 bg-slate-900 text-white rounded text-xs font-semibold hover:bg-black transition-colors"
            >
              Create First Subject
            </button>
          </div>
        )}
      </div>

      {/* Source Material Upload */}
      <div>
        <label className="block text-sm font-bold uppercase tracking-wide text-slate-700 mb-2">
          Source Material (TXT, PDF, DOCX)
        </label>
        <div
          className={`mt-1 border-2 border-dashed rounded-xl p-10 text-center transition-colors relative ${
            dragActive
              ? "border-slate-900 bg-slate-50"
              : "border-gray-300 hover:border-slate-400"
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            accept=".txt,.pdf,.docx"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            onChange={(e) => setFile(e.target.files[0])}
          />

          {!file ? (
            <div className="flex flex-col items-center pointer-events-none">
              <UploadCloud className="w-10 h-10 text-slate-400 mb-4" />
              <p className="text-lg font-medium text-slate-900">
                Drag & drop your file here
              </p>
              <p className="text-sm text-slate-500 mt-1">
                or click to browse from your computer (TXT, PDF, DOCX)
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center pointer-events-none">
              <div className="bg-slate-100 p-4 rounded-full mb-3">
                <FileText className="w-8 h-8 text-slate-900" />
              </div>
              <p className="text-lg font-bold text-slate-900">{file.name}</p>
              <p className="text-sm text-slate-500 mt-1">
                {(file.size / 1024).toFixed(1)} KB — Ready to analyze
              </p>
            </div>
          )}
        </div>

        {file && (
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              onClick={() => setFile(null)}
              className="text-sm text-red-600 font-medium hover:text-red-800 flex items-center cursor-pointer"
            >
              <X className="w-4 h-4 mr-1" /> Remove File
            </button>
          </div>
        )}
      </div>

      {/* Submit: Analyze */}
      <div className="pt-4 border-t border-gray-100 flex justify-end">
        <button
          type="submit"
          disabled={isAnalyzing}
          className="bg-slate-900 hover:bg-black text-white px-8 py-4 rounded-lg font-bold text-lg flex items-center transition-colors disabled:opacity-70 disabled:cursor-not-allowed cursor-pointer shadow-md"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="w-6 h-6 mr-3 animate-spin" />
              Analyzing Document with AI...
            </>
          ) : (
            <>
              <Sparkles className="w-6 h-6 mr-2" />
              Analyze & Configure Exam
            </>
          )}
        </button>
      </div>
    </form>
  );

  // ——— Render: Step 2 — Review analysis & configure exam ———
  const renderConfigureStep = () => {
    const analysis = analysisResult;
    const dist = analysis?.recommended_distribution || {};

    return (
      <div className="space-y-8">
        {/* Back button */}
        <button
          type="button"
          onClick={handleBackToUpload}
          className="text-sm text-slate-600 hover:text-slate-900 font-medium flex items-center gap-1 cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" /> Upload a Different File
        </button>

        {/* Analysis Summary Card */}
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6 space-y-5">
          <div className="flex items-center gap-2 mb-1">
            <Brain className="w-5 h-5 text-indigo-600" />
            <h3 className="font-bold text-lg text-slate-900">AI Document Analysis</h3>
            <span className="ml-auto px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              Complete
            </span>
          </div>

          {/* File info */}
          {analysis?.document_stats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <div className="bg-white/70 rounded-lg p-3 border border-blue-100">
                <div className="text-xs text-slate-500 uppercase font-semibold">File</div>
                <div className="font-medium text-slate-900 truncate">
                  {analysis.document_stats.original_file_name || file?.name}
                </div>
              </div>
              <div className="bg-white/70 rounded-lg p-3 border border-blue-100">
                <div className="text-xs text-slate-500 uppercase font-semibold">Words</div>
                <div className="font-bold text-slate-900">
                  {analysis.document_stats.estimated_words?.toLocaleString() || "—"}
                </div>
              </div>
              <div className="bg-white/70 rounded-lg p-3 border border-blue-100">
                <div className="text-xs text-slate-500 uppercase font-semibold">Sections</div>
                <div className="font-bold text-slate-900">
                  {analysis.document_stats.chunk_count || "—"}
                </div>
              </div>
              <div className="bg-white/70 rounded-lg p-3 border border-blue-100">
                <div className="text-xs text-slate-500 uppercase font-semibold">Type</div>
                <div className="font-bold text-slate-900 uppercase">
                  {analysis.document_stats.file_type || "—"}
                </div>
              </div>
            </div>
          )}

          {/* Summary */}
          <div>
            <p className="text-xs font-bold uppercase text-slate-500 mb-1">Summary</p>
            <p className="text-sm text-slate-700 leading-relaxed">{analysis?.summary}</p>
          </div>

          {/* Topics & Concepts */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-bold uppercase text-slate-500 mb-2 flex items-center gap-1">
                <Target className="w-3.5 h-3.5" /> Key Topics
              </p>
              <div className="flex flex-wrap gap-1.5">
                {analysis?.key_topics?.map((topic, i) => (
                  <span
                    key={i}
                    className="px-2.5 py-1 bg-white border border-blue-200 text-blue-800 text-xs rounded-full font-medium"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-bold uppercase text-slate-500 mb-2 flex items-center gap-1">
                <ListChecks className="w-3.5 h-3.5" /> Key Concepts
              </p>
              <div className="flex flex-wrap gap-1.5">
                {analysis?.key_concepts?.map((concept, i) => (
                  <span
                    key={i}
                    className="px-2.5 py-1 bg-white border border-indigo-200 text-indigo-800 text-xs rounded-full font-medium"
                  >
                    {concept}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Learning Objectives */}
          {analysis?.learning_objectives?.length > 0 && (
            <div>
              <p className="text-xs font-bold uppercase text-slate-500 mb-2">Learning Objectives</p>
              <ul className="space-y-1.5">
                {analysis.learning_objectives.map((obj, i) => (
                  <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                    {obj}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* AI-recommended distribution */}
          <div>
            <p className="text-xs font-bold uppercase text-slate-500 mb-2 flex items-center gap-1">
              <BarChart3 className="w-3.5 h-3.5" /> Recommended Question Distribution
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {[
                { label: "Multiple Choice", key: "multiple_choice" },
                { label: "True / False", key: "true_false" },
                { label: "Identification", key: "identification" },
                { label: "Essay", key: "essay" },
                { label: "Matching", key: "matching" },
              ].map(({ label, key }) => (
                <div
                  key={key}
                  className="bg-white/70 rounded-lg p-2.5 text-center border border-blue-100"
                >
                  <div className="text-lg font-bold text-slate-900">{dist[key] || 0}</div>
                  <div className="text-[10px] text-slate-500 uppercase font-semibold leading-tight">
                    {label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Difficulty assessment */}
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase text-slate-500">AI Difficulty:</span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase ${
                  analysis?.estimated_difficulty === "hard"
                    ? "bg-red-100 text-red-800"
                    : analysis?.estimated_difficulty === "easy"
                    ? "bg-green-100 text-green-800"
                    : "bg-yellow-100 text-yellow-800"
                }`}
              >
                {analysis?.estimated_difficulty || "medium"}
              </span>
            </div>
            {analysis?.difficulty_reasoning && (
              <span className="text-xs text-slate-500 italic">
                {analysis.difficulty_reasoning}
              </span>
            )}
          </div>
        </div>

        {/* Configuration Form — pre-filled with AI suggestions */}
        <form onSubmit={handleGenerate} className="space-y-6">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-5 h-5 text-amber-500" />
            <h3 className="font-bold text-lg text-slate-900">
              Review & Adjust Exam Settings
            </h3>
          </div>
          <p className="text-sm text-slate-500 -mt-4">
            The fields below have been pre-filled based on AI analysis. Adjust anything before generating.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="col-span-1 md:col-span-2">
              <label className="block text-sm font-bold uppercase tracking-wide text-slate-700 mb-2">
                Exam Title
              </label>
              <input
                required
                type="text"
                name="exam_title"
                value={formData.exam_title}
                onChange={handleInputChange}
                placeholder="e.g., Midterm: Data Structures"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900 transition-colors"
              />
            </div>

            <div className="col-span-1 md:col-span-2">
              <label className="block text-sm font-bold uppercase tracking-wide text-slate-700 mb-2">
                Description
              </label>
              <textarea
                name="exam_description"
                value={formData.exam_description}
                onChange={handleInputChange}
                rows={3}
                placeholder="Optional exam description..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900 transition-colors resize-none"
              />
            </div>

            <div>
              <label className="block text-sm font-bold uppercase tracking-wide text-slate-700 mb-2">
                Question Type
              </label>
              <select
                name="exam_type"
                value={formData.exam_type}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
              >
                <option value="all">Mixed (All Types)</option>
                <option value="multiple_choice">Multiple Choice</option>
                <option value="matching">Matching</option>
                <option value="true_false">True / False</option>
                <option value="identification">Identification</option>
                <option value="essay">Essay</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-bold uppercase tracking-wide text-slate-700 mb-2">
                Difficulty
              </label>
              <select
                name="difficulty"
                value={formData.difficulty}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-slate-900"
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>

            <div className="grid grid-cols-3 gap-4 col-span-1 md:col-span-2">
              <div>
                <label className="block text-sm font-bold uppercase tracking-wide text-slate-700 mb-2">
                  Total Q's
                </label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  name="total_questions"
                  value={formData.total_questions}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div>
                <label className="block text-sm font-bold uppercase tracking-wide text-slate-700 mb-2">
                  Time (Min)
                </label>
                <input
                  type="number"
                  min="1"
                  name="time_limit_minutes"
                  value={formData.time_limit_minutes}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div>
                <label className="block text-sm font-bold uppercase tracking-wide text-slate-700 mb-2">
                  Passing %
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  name="passing_score"
                  value={formData.passing_score}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
            </div>
          </div>

          {/* Submit: Generate */}
          <div className="pt-4 border-t border-gray-100 flex justify-end">
            <button
              type="submit"
              disabled={isSubmitting}
              className="bg-slate-900 hover:bg-black text-white px-8 py-4 rounded-lg font-bold text-lg flex items-center transition-colors disabled:opacity-70 disabled:cursor-not-allowed cursor-pointer shadow-md"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-6 h-6 mr-3 animate-spin" />
                  Generating Examination via AI...
                </>
              ) : (
                <>
                  Generate Examination <ChevronRight className="w-6 h-6 ml-2" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-8 bg-white border border-gray-200 shadow-sm rounded-xl text-slate-900 font-sans">
      <div className="mb-8 border-b border-gray-100 pb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight mb-2 text-slate-900">
            Generate Examination
          </h2>
          <p className="text-slate-500">
            {step === "upload"
              ? "Upload your source material and the AI will analyze it to recommend exam settings."
              : "Review the AI analysis below and adjust settings before generating your exam."}
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-2 shrink-0">
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${
              step === "upload"
                ? "bg-slate-900 text-white"
                : "bg-emerald-100 text-emerald-800"
            }`}
          >
            {step === "upload" ? (
              <>
                <UploadCloud className="w-3.5 h-3.5" /> 1. Upload & Analyze
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" /> 1. Analyzed
              </>
            )}
          </div>
          <ChevronRight className="w-4 h-4 text-slate-300" />
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${
              step === "configure"
                ? "bg-slate-900 text-white"
                : "bg-slate-100 text-slate-400"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" /> 2. Configure & Generate
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3 text-red-800">
          <AlertCircle className="w-5 h-5 mt-0.5 text-red-600 shrink-0" />
          <div className="text-sm font-medium">{errorMessage}</div>
        </div>
      )}

      {successMessage && (
        <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-start gap-3 text-emerald-800">
          <CheckCircle2 className="w-5 h-5 mt-0.5 text-emerald-600 shrink-0" />
          <div className="text-sm font-medium">{successMessage}</div>
        </div>
      )}

      {/* Modal for creating a new subject */}
      {showNewSubjectModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl border border-gray-200 max-w-md w-full p-6 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg text-slate-900">Create New Subject</h3>
              <button
                type="button"
                onClick={() => setShowNewSubjectModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                  Subject Name
                </label>
                <input
                  type="text"
                  value={newSubjectName}
                  onChange={(e) => setNewSubjectName(e.target.value)}
                  placeholder="e.g., Computer Science 101"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                  Subject Code
                </label>
                <input
                  type="text"
                  value={newSubjectCode}
                  onChange={(e) => setNewSubjectCode(e.target.value)}
                  placeholder="e.g., CS101"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewSubjectModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-slate-600 hover:bg-slate-50 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={creatingSubject}
                  onClick={handleCreateSubject}
                  className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-semibold hover:bg-black transition-colors disabled:opacity-50"
                >
                  {creatingSubject ? "Creating..." : "Save Subject"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {step === "upload" ? renderUploadStep() : renderConfigureStep()}
    </div>
  );
}

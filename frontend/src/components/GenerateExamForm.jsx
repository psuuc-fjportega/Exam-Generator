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
} from "lucide-react";

export default function GenerateExamForm({ onExamGenerated, token: propToken }) {
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Subjects state
  const [subjects, setSubjects] = useState([]);
  const [loadingSubjects, setLoadingSubjects] = useState(false);
  const [showNewSubjectModal, setShowNewSubjectModal] = useState(false);
  const [newSubjectName, setNewSubjectName] = useState("");
  const [newSubjectCode, setNewSubjectCode] = useState("");
  const [creatingSubject, setCreatingSubject] = useState(false);

  // Form State matching backend requirements
  const [formData, setFormData] = useState({
    subject_id: "",
    exam_title: "",
    exam_type: "all",
    total_questions: "5",
    difficulty: "medium",
    time_limit_minutes: "60",
    passing_score: "50",
    exam_description: "",
  });

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");

    const token = getActiveToken();
    if (!token) {
      setErrorMessage("You must be logged in as a teacher. Please sign in or use the Teacher Login button above.");
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

    setIsSubmitting(true);

    const payload = new FormData();
    Object.keys(formData).forEach((key) => {
      if (formData[key] !== "") {
        payload.append(key, formData[key]);
      }
    });
    payload.append("file", file);

    try {
      const response = await fetch("/api/materials/upload-and-generate", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: payload,
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

  return (
    <div className="max-w-4xl mx-auto p-8 bg-white border border-gray-200 shadow-sm rounded-xl text-slate-900 font-sans">
      <div className="mb-8 border-b border-gray-100 pb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight mb-2 text-slate-900">
            Generate Examination
          </h2>
          <p className="text-slate-500">
            Configure parameters and upload source materials to automatically generate a validated exam.
          </p>
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

      <form onSubmit={handleSubmit} className="space-y-8">
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

        {/* Configuration Grid */}
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
                  {(file.size / 1024).toFixed(1)} KB — Ready to upload
                </p>
              </div>
            )}
          </div>

          {/* File Removal Toggle */}
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

        {/* Submit Action */}
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
}

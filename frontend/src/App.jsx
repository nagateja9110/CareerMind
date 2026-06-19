import React, { useEffect, useRef, useState } from "react";
import {
  BadgeCheck,
  BriefcaseBusiness,
  ChevronUp,
  FileText,
  LoaderCircle,
  LogOut,
  MessageSquareText,
  Search,
  UploadCloud,
  UserRound,
  X,
} from "lucide-react";

import {
  clearSession,
  fetchChatHistory,
  fetchChatThread,
  fetchProfile,
  fetchResume,
  getStoredAccessToken,
  login,
  register,
  searchJobs,
  sendChatMessage,
  setOnAuthFailure,
  setSession,
  uploadResume,
} from "./api";
import "./styles.css";

const starterPrompts = [
  "What skills am I missing for Data Engineer roles?",
  "Which jobs match my current profile?",
  "How do I move from backend to ML engineering?",
];

const USER_STORAGE_KEY = "careermind_user";
const ACTIVE_CHAT_STORAGE_KEY = "careermind_active_chat";

function getCachedUser() {
  const cached = localStorage.getItem(USER_STORAGE_KEY);
  if (!cached) {
    return null;
  }

  try {
    return JSON.parse(cached);
  } catch {
    localStorage.removeItem(USER_STORAGE_KEY);
    return null;
  }
}

function formatApiError(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg ?? item.type ?? "Invalid input").join(" ");
  }
  return fallback;
}

function App() {
  const fileInputRef = useRef(null);
  const profileMenuRef = useRef(null);
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({
    name: "",
    email: "",
    password: "",
  });
  const [token, setToken] = useState(getStoredAccessToken);
  const [user, setUser] = useState(getCachedUser);
  const [chatInput, setChatInput] = useState("");
  const [jobSearchForm, setJobSearchForm] = useState({
    role: "Data Engineer",
    location: "Bangalore",
    skills: "Python, SQL",
  });
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [history, setHistory] = useState([]);
  const [resume, setResume] = useState(null);
  const [recommendedJobs, setRecommendedJobs] = useState([]);
  const [searchedJobs, setSearchedJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(Boolean(token));
  const [bootstrapError, setBootstrapError] = useState("");
  const [bootstrapRetryToken, setBootstrapRetryToken] = useState(0);
  const [error, setError] = useState("");
  const [resumeUploadNotice, setResumeUploadNotice] = useState("");
  const [hasSearchedJobs, setHasSearchedJobs] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showResumeModal, setShowResumeModal] = useState(false);
  const [showResumeText, setShowResumeText] = useState(false);

  useEffect(() => {
    if (!showProfileMenu) {
      return;
    }

    function handleOutsideClick(event) {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target)) {
        setShowProfileMenu(false);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [showProfileMenu]);

  useEffect(() => {
    // Lets the axios interceptor force a logout when a 401 survives a refresh attempt.
    setOnAuthFailure(handleLogout);
  }, []);

  useEffect(() => {
    if (activeChatId) {
      localStorage.setItem(ACTIVE_CHAT_STORAGE_KEY, activeChatId);
    } else {
      localStorage.removeItem(ACTIVE_CHAT_STORAGE_KEY);
    }
  }, [activeChatId]);

  useEffect(() => {
    if (!token) {
      setBootstrapping(false);
      return;
    }

    let cancelled = false;

    async function bootstrap() {
      setBootstrapError("");
      try {
        const [profile, resumeResponse, historyResponse] = await Promise.all([
          fetchProfile(),
          fetchResume().catch(() => null),
          fetchChatHistory(),
        ]);

        if (cancelled) {
          return;
        }

        setUser(profile);
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(profile));
        setResume(resumeResponse);
        setHistory(historyResponse);

        const savedChatId = localStorage.getItem(ACTIVE_CHAT_STORAGE_KEY);
        if (savedChatId && historyResponse.some((chat) => chat.chat_id === savedChatId)) {
          const thread = await fetchChatThread(savedChatId).catch(() => null);
          if (thread && !cancelled) {
            setActiveChatId(thread.chat_id);
            setMessages(thread.messages);
          }
        }
      } catch (bootstrapError) {
        if (cancelled) {
          return;
        }
        // An expired/invalid token is the only case that should force a fresh login.
        // Network hiccups or a slow backend cold start must not wipe the cached
        // session and resume data, or every reload during a hiccup looks like data loss.
        if (bootstrapError?.response?.status === 401) {
          handleLogout();
          return;
        }
        setBootstrapError(
          "Couldn't reach the server to refresh your data. Showing what's cached locally — retry when you're ready.",
        );
      } finally {
        if (!cancelled) {
          setBootstrapping(false);
        }
      }
    }

    bootstrap();

    return () => {
      cancelled = true;
    };
  }, [token, bootstrapRetryToken]);

  function persistSession(authResponse) {
    setSession(authResponse.tokens);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(authResponse.user));
    setToken(authResponse.tokens.access_token);
    setUser(authResponse.user);
  }

  function handleLogout() {
    clearSession();
    localStorage.removeItem(USER_STORAGE_KEY);
    localStorage.removeItem(ACTIVE_CHAT_STORAGE_KEY);
    setToken("");
    setUser(null);
    setResume(null);
    setHistory([]);
    setMessages([]);
    setRecommendedJobs([]);
    setActiveChatId(null);
    setError("");
    setBootstrapping(false);
  }

  async function handleAuthSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const action = authMode === "login" ? login : register;
      const payload =
        authMode === "login"
          ? { email: authForm.email, password: authForm.password }
          : authForm;
      const response = await action(payload);
      persistSession(response);
      const [resumeResponse, historyResponse] = await Promise.all([
        fetchResume().catch(() => null),
        fetchChatHistory(),
      ]);
      setResume(resumeResponse);
      setHistory(historyResponse);
      setAuthForm({ name: "", email: "", password: "" });
    } catch (requestError) {
      setError(formatApiError(requestError, "Could not complete authentication. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  async function handleResumeSelection(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setError("");
    setLoading(true);

    try {
      const response = await uploadResume(file);
      setResume(response);
      const skillCount = response.parsed_skills?.length ?? 0;
      setResumeUploadNotice(
        skillCount
          ? `Resume uploaded — detected ${skillCount} skill${skillCount === 1 ? "" : "s"}.`
          : "Resume uploaded, but no recognizable skills were detected.",
      );
    } catch (requestError) {
      setError(
        formatApiError(
          requestError,
          "Resume upload failed. Please try a text file or a text-based PDF.",
        ),
      );
    } finally {
      setLoading(false);
      event.target.value = "";
    }
  }

  useEffect(() => {
    if (!resumeUploadNotice) {
      return;
    }
    const timeout = setTimeout(() => setResumeUploadNotice(""), 5000);
    return () => clearTimeout(timeout);
  }, [resumeUploadNotice]);

  async function handleSendMessage(messageOverride) {
    const message = (messageOverride ?? chatInput).trim();
    if (!message) {
      return;
    }

    const optimisticUserMessage = {
      role: "user",
      content: message,
      timestamp: new Date().toISOString(),
    };

    setError("");
    setLoading(true);
    setMessages((current) => [...current, optimisticUserMessage]);
    setChatInput("");

    try {
      const response = await sendChatMessage({
        chat_id: activeChatId,
        message,
      });

      const assistantMessage = {
        role: "assistant",
        content: response.answer,
        timestamp: new Date().toISOString(),
      };

      setMessages((current) => [...current, assistantMessage]);
      setActiveChatId(response.chat_id);
      setRecommendedJobs(response.recommended_jobs);
      // A new chat turn supersedes any earlier direct job search, so its
      // "no results" message shouldn't keep showing alongside fresh recommendations.
      setSearchedJobs([]);
      setHasSearchedJobs(false);
      const historyResponse = await fetchChatHistory();
      setHistory(historyResponse);
    } catch (requestError) {
      setMessages((current) => current.slice(0, -1));
      setChatInput(message);
      setError(formatApiError(requestError, "The chat request failed. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectChat(chatId) {
    setLoading(true);
    setError("");
    try {
      const thread = await fetchChatThread(chatId);
      setActiveChatId(thread.chat_id);
      setMessages(thread.messages);
      setRecommendedJobs([]);
    } catch {
      setError("Could not load that chat thread.");
    } finally {
      setLoading(false);
    }
  }

  async function handleJobSearch(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const jobs = await searchJobs({
        role: jobSearchForm.role.trim(),
        location: jobSearchForm.location.trim(),
        skills: jobSearchForm.skills
          .split(",")
          .map((skill) => skill.trim())
          .filter(Boolean),
      });
      setSearchedJobs(jobs);
      setHasSearchedJobs(true);
      // A direct search supersedes earlier chat-driven recommendations in the same panel.
      setRecommendedJobs([]);
    } catch (requestError) {
      setError(formatApiError(requestError, "Job search failed. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  function handleRetryBootstrap() {
    setBootstrapping(true);
    setBootstrapRetryToken((current) => current + 1);
  }

  function handleNewChat() {
    setActiveChatId(null);
    setMessages([]);
    setRecommendedJobs([]);
    setSearchedJobs([]);
    setHasSearchedJobs(false);
    setChatInput("");
    setError("");
  }

  if (bootstrapping) {
    return (
      <main className="boot-screen">
        <LoaderCircle className="spin" size={28} />
        <p>Loading your workspace...</p>
      </main>
    );
  }

  if (!token || !user) {
    return (
      <main className="auth-shell">
        <section className="auth-panel">
          <div className="auth-brand">
            <BriefcaseBusiness size={26} aria-hidden="true" />
            <span>CareerMind</span>
          </div>
          <p className="eyebrow">Career advisor</p>
          <h1>Ground your next move in profile data and live job signals.</h1>
          <p className="auth-copy">
            Sign in to upload your resume, compare yourself against target roles,
            and keep a persistent chat history.
          </p>

          <div className="auth-toggle" role="tablist" aria-label="Auth mode">
            <button
              className={authMode === "login" ? "toggle-active" : ""}
              type="button"
              onClick={() => setAuthMode("login")}
            >
              Login
            </button>
            <button
              className={authMode === "register" ? "toggle-active" : ""}
              type="button"
              onClick={() => setAuthMode("register")}
            >
              Register
            </button>
          </div>

          <form className="auth-form" onSubmit={handleAuthSubmit}>
            {authMode === "register" ? (
              <input
                value={authForm.name}
                onChange={(event) =>
                  setAuthForm((current) => ({ ...current, name: event.target.value }))
                }
                placeholder="Your name"
                required
              />
            ) : null}
            <input
              value={authForm.email}
              onChange={(event) =>
                setAuthForm((current) => ({ ...current, email: event.target.value }))
              }
              placeholder="Email"
              type="email"
              required
            />
            <input
              value={authForm.password}
              onChange={(event) =>
                setAuthForm((current) => ({ ...current, password: event.target.value }))
              }
              placeholder="Password"
              type="password"
              required
            />
            <button type="submit" disabled={loading}>
              {loading ? "Working..." : authMode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>

          {error ? <p className="error-banner">{error}</p> : null}
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Conversation history">
        <div className="brand">
          <BriefcaseBusiness size={24} aria-hidden="true" />
          <span>CareerMind</span>
        </div>
        <button className="new-chat-button" type="button" onClick={handleNewChat}>
          <MessageSquareText size={18} aria-hidden="true" />
          New chat
        </button>

        <button
          className="sidebar-resume-trigger"
          type="button"
          onClick={() => setShowResumeModal(true)}
        >
          <BadgeCheck size={16} aria-hidden="true" />
          <span>Resume profile</span>
          {resume ? <span className="resume-dot" aria-hidden="true" /> : null}
        </button>

        <form className="sidebar-section job-search-form" onSubmit={handleJobSearch}>
          <div className="sidebar-label">
            <Search size={16} aria-hidden="true" />
            <span>Job search</span>
          </div>
          <input
            aria-label="Role"
            value={jobSearchForm.role}
            onChange={(event) =>
              setJobSearchForm((current) => ({ ...current, role: event.target.value }))
            }
            placeholder="Role"
          />
          <input
            aria-label="Location"
            value={jobSearchForm.location}
            onChange={(event) =>
              setJobSearchForm((current) => ({ ...current, location: event.target.value }))
            }
            placeholder="Location"
          />
          <input
            aria-label="Skills"
            value={jobSearchForm.skills}
            onChange={(event) =>
              setJobSearchForm((current) => ({ ...current, skills: event.target.value }))
            }
            placeholder="Skills"
          />
          <button type="submit" disabled={loading}>
            Search jobs
          </button>
        </form>

        <div className="history-list">
          {history.length ? (
            history.map((chat) => (
              <button
                className={`history-item ${activeChatId === chat.chat_id ? "history-item-active" : ""}`}
                key={chat.chat_id}
                type="button"
                onClick={() => handleSelectChat(chat.chat_id)}
              >
                <span>{chat.title}</span>
              </button>
            ))
          ) : (
            <div className="history-empty">Your saved chats will show up here.</div>
          )}
        </div>

        <div className="sidebar-profile" ref={profileMenuRef}>
          {showProfileMenu ? (
            <div className="sidebar-profile-menu">
              <p className="sidebar-meta">{user.email}</p>
              <button className="logout-button" type="button" onClick={handleLogout}>
                <LogOut size={16} aria-hidden="true" />
                Log out
              </button>
            </div>
          ) : null}
          <button
            className="sidebar-profile-trigger"
            type="button"
            onClick={() => setShowProfileMenu((current) => !current)}
            aria-expanded={showProfileMenu}
          >
            <UserRound size={18} aria-hidden="true" />
            <span>{user.name}</span>
            <ChevronUp size={16} aria-hidden="true" className={showProfileMenu ? "" : "chevron-flipped"} />
          </button>
        </div>
      </aside>

      <section className="workspace" aria-label="Career advisor chat">
        <div className="workspace-top">
          <header className="workspace-header">
            <div>
              <p className="eyebrow">Career advisor</p>
              <h1>Ask grounded questions about your next role.</h1>
            </div>
            <button
              className="upload-button"
              type="button"
              onClick={() => fileInputRef.current?.click()}
            >
              <UploadCloud size={18} aria-hidden="true" />
              Upload resume
            </button>
            <input
              ref={fileInputRef}
              className="hidden-input"
              type="file"
              accept=".txt,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleResumeSelection}
            />
          </header>

          {bootstrapError ? (
            <p className="error-banner banner-inline">
              {bootstrapError}{" "}
              <button type="button" className="banner-retry" onClick={handleRetryBootstrap}>
                Retry
              </button>
            </p>
          ) : null}

          {resumeUploadNotice ? (
            <p className="success-banner banner-inline">{resumeUploadNotice}</p>
          ) : null}
        </div>

        <div className="chat-panel">
          {messages.length ? (
            <div className="message-stack">
              {messages.map((message, index) => (
                <div
                  className={message.role === "user" ? "user-message" : "assistant-message"}
                  key={`${message.timestamp}-${index}`}
                >
                  <span className="message-label">
                    {message.role === "user" ? "You" : "Agent"}
                  </span>
                  <p>{message.content}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="assistant-message">
              <span className="message-label">Agent</span>
              <p>
                Upload a resume or start with a question. I will use role skills,
                job listings, and your background to explain the recommendation.
              </p>
            </div>
          )}

          {messages.length === 0 ? (
            <div className="prompt-row" aria-label="Starter prompts">
              {starterPrompts.map((prompt) => (
                <button
                  className="prompt-chip"
                  type="button"
                  key={prompt}
                  onClick={() => handleSendMessage(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          ) : null}

          {searchedJobs.length ? (
            <section className="jobs-band" aria-label="Direct job search results">
              {searchedJobs.map((job) => (
                <article className="job-card" key={`search-${job.company}-${job.title}`}>
                  <p className="job-meta">{job.location}</p>
                  <h2>{job.title}</h2>
                  <p className="job-company">{job.company}</p>
                  <div className="skill-grid">
                    {job.matched_skills.map((skill) => (
                      <span className="skill-chip" key={`search-${job.title}-${skill}`}>
                        {skill}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </section>
          ) : null}

          {hasSearchedJobs && !searchedJobs.length ? (
            <p className="sidebar-meta">
              No job postings matched that search. Try a broader role, location, or skill list.
            </p>
          ) : null}

          {recommendedJobs.length ? (
            <section className="jobs-band" aria-label="Recommended jobs">
              {recommendedJobs.map((job) => (
                <article className="job-card" key={`${job.company}-${job.title}`}>
                  <p className="job-meta">{job.location}</p>
                  <h2>{job.title}</h2>
                  <p className="job-company">{job.company}</p>
                  <div className="skill-grid">
                    {job.matched_skills.map((skill) => (
                      <span className="skill-chip" key={`${job.title}-${skill}`}>
                        {skill}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </section>
          ) : null}

          {error ? <p className="error-banner">{error}</p> : null}
        </div>

        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            handleSendMessage();
          }}
        >
          <input
            aria-label="Message"
            placeholder="Ask about skill gaps, target roles, or hiring companies..."
            value={chatInput}
            onChange={(event) => setChatInput(event.target.value)}
          />
          <button disabled={loading} type="submit">
            {loading ? "Thinking..." : "Send"}
          </button>
        </form>
      </section>

      {showResumeModal ? (
        <div
          className="modal-overlay"
          onClick={() => {
            setShowResumeModal(false);
            setShowResumeText(false);
          }}
        >
          <div className="modal-panel" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h2>Resume profile</h2>
              <button
                className="modal-close"
                type="button"
                onClick={() => {
                  setShowResumeModal(false);
                  setShowResumeText(false);
                }}
                aria-label="Close"
              >
                <X size={18} aria-hidden="true" />
              </button>
            </div>

            {resume ? (
              <div className="modal-body">
                <p className="sidebar-meta sidebar-meta-confirm">
                  Uploaded {new Date(resume.uploaded_at).toLocaleDateString()}
                </p>
                <div className="skill-grid">
                  {resume.parsed_skills.map((skill) => (
                    <span className="skill-chip" key={skill}>
                      {skill}
                    </span>
                  ))}
                </div>
                <p className="sidebar-meta">
                  {resume.experience_years
                    ? `${resume.experience_years} years detected`
                    : "Experience not detected"}
                </p>

                <button
                  className="modal-secondary-button"
                  type="button"
                  onClick={() => setShowResumeText((current) => !current)}
                >
                  <FileText size={16} aria-hidden="true" />
                  {showResumeText ? "Hide uploaded resume" : "View uploaded resume"}
                </button>
                {showResumeText ? <pre className="resume-text">{resume.raw_text}</pre> : null}

                <button
                  className="modal-secondary-button"
                  type="button"
                  onClick={() => {
                    setShowResumeModal(false);
                    setShowResumeText(false);
                    fileInputRef.current?.click();
                  }}
                >
                  <UploadCloud size={16} aria-hidden="true" />
                  Upload a new resume
                </button>
              </div>
            ) : (
              <div className="modal-body">
                <p className="sidebar-meta">Upload a resume to personalize the agent.</p>
                <button
                  className="modal-secondary-button"
                  type="button"
                  onClick={() => {
                    setShowResumeModal(false);
                    fileInputRef.current?.click();
                  }}
                >
                  <UploadCloud size={16} aria-hidden="true" />
                  Upload resume
                </button>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </main>
  );
}

export default App;

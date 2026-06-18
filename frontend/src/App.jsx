import React, { useEffect, useRef, useState } from "react";
import {
  BadgeCheck,
  BriefcaseBusiness,
  LoaderCircle,
  LogOut,
  MessageSquareText,
  Search,
  Sparkles,
  UploadCloud,
  UserRound,
} from "lucide-react";

import {
  fetchChatHistory,
  fetchChatThread,
  fetchProfile,
  fetchResume,
  login,
  register,
  searchJobs,
  sendChatMessage,
  setAccessToken,
  uploadResume,
} from "./api";
import "./styles.css";

const starterPrompts = [
  "What skills am I missing for Data Engineer roles?",
  "Which jobs match my current profile?",
  "How do I move from backend to ML engineering?",
];

const TOKEN_STORAGE_KEY = "careermind_access_token";
const USER_STORAGE_KEY = "careermind_user";

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
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({
    name: "",
    email: "",
    password: "",
  });
  const [token, setToken] = useState(localStorage.getItem(TOKEN_STORAGE_KEY) ?? "");
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
  const [toolCalls, setToolCalls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(Boolean(token));
  const [error, setError] = useState("");

  useEffect(() => {
    setAccessToken(token);
  }, [token]);

  useEffect(() => {
    if (!token) {
      setBootstrapping(false);
      return;
    }

    let cancelled = false;

    async function bootstrap() {
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
      } catch {
        handleLogout();
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
  }, [token]);

  function persistSession(authResponse) {
    localStorage.setItem(TOKEN_STORAGE_KEY, authResponse.tokens.access_token);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(authResponse.user));
    setToken(authResponse.tokens.access_token);
    setUser(authResponse.user);
  }

  function handleLogout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
    setAccessToken("");
    setToken("");
    setUser(null);
    setResume(null);
    setHistory([]);
    setMessages([]);
    setToolCalls([]);
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
      setToolCalls(response.tool_calls);
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
      setToolCalls([]);
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
    } catch (requestError) {
      setError(formatApiError(requestError, "Job search failed. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  function handleNewChat() {
    setActiveChatId(null);
    setMessages([]);
    setRecommendedJobs([]);
    setSearchedJobs([]);
    setToolCalls([]);
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

        <div className="sidebar-section">
          <div className="sidebar-label">
            <UserRound size={16} aria-hidden="true" />
            <span>{user.name}</span>
          </div>
          <p className="sidebar-meta">{user.email}</p>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-label">
            <BadgeCheck size={16} aria-hidden="true" />
            <span>Resume profile</span>
          </div>
          {resume ? (
            <>
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
            </>
          ) : (
            <p className="sidebar-meta">Upload a resume to personalize the agent.</p>
          )}
        </div>

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

        <button className="logout-button" type="button" onClick={handleLogout}>
          <LogOut size={16} aria-hidden="true" />
          Log out
        </button>
      </aside>

      <section className="workspace" aria-label="Career advisor chat">
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
            accept=".txt,.pdf,text/plain,application/pdf"
            onChange={handleResumeSelection}
          />
        </header>

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

          {toolCalls.length ? (
            <div className="tool-panel">
              <div className="sidebar-label">
                <Sparkles size={16} aria-hidden="true" />
                <span>Agent steps</span>
              </div>
              <div className="tool-call-list">
                {toolCalls.map((toolCall, index) => (
                  <div className="tool-call" key={`${toolCall.tool}-${index}`}>
                    <strong>{toolCall.tool}</strong>
                    <span>{JSON.stringify(toolCall.output)}</span>
                  </div>
                ))}
              </div>
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
    </main>
  );
}

export default App;

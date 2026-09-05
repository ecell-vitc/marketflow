import React, { useState } from "react";
import { makeRequest, showMessage } from "../../lib/utils";

const AdminLogin = ({ onSuccess }: { onSuccess: () => void }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = await makeRequest("admin/login", "POST", { username, password });

      if (payload.detail) {
        showMessage(payload.detail.message || "Login failed", true);
        return;
      }

      localStorage.setItem("admin_token", payload.token);
      onSuccess();
    } catch (err) {
      console.log(err);
      showMessage("An unexpected error occurred. Please try again", true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-[420px] mx-auto mt-[6rem] rounded-3xl p-10 bg-gradient-to-br from-[#12133f] via-[#1b1c55] to-[#17184a] shadow-2xl border border-white/10">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-semibold text-white">Admin Login</h1>
      </div>

      <form className="space-y-6" onSubmit={handleSubmit}>
        <div>
          <label className="block text-sm text-gray-200 mb-2">Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-3 py-2 rounded-full bg-white/20 text-white placeholder-gray-300 outline-none border border-white/10 focus:ring-2 focus:ring-green-400/70"
          />
        </div>

        <div>
          <label className="block text-sm text-gray-200 mb-2">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 rounded-full bg-white/20 text-white placeholder-gray-300 outline-none border border-white/10 focus:ring-2 focus:ring-green-400/70"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-4 rounded-full bg-gradient-to-r from-[#6ee38f] to-[#3ca76a] text-white font-medium text-lg hover:opacity-90 transition disabled:opacity-60"
        >
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>
    </div>
  );
};

const AdminPanel = () => {
  const [username, setUsername] = useState("");
  const [message, setMessage] = useState("");
  const [stockName, setStockName] = useState("");
  const [stockCategory, setStockCategory] = useState("");
  const [stockValue, setStockValue] = useState("5000");
  const [testEmails, setTestEmails] = useState("");
  const [testUsersResult, setTestUsersResult] = useState<{
    created: string[];
    skipped: string[];
    password: string;
  } | null>(null);

  const call = async (path: string, method: string, data?: Record<string, unknown>) => {
    const payload = await makeRequest(path, method, data, true, "admin_token");
    if (payload.detail) showMessage(payload.detail.message || "Request failed", true);
    else showMessage(payload.message || "Done");
  };

  const handleCreateStock = async () => {
    if (!stockName.trim() || !stockCategory.trim()) return;

    const payload = await makeRequest(
      "admin/stocks",
      "POST",
      { stocks: [{ name: stockName, category: stockCategory, value: Number(stockValue) || 5000 }] },
      true,
      "admin_token"
    );

    if (payload.detail) {
      showMessage(payload.detail.message || "Request failed", true);
      return;
    }

    showMessage(`Created stock: ${payload.created.join(", ")}`);
    setStockName("");
    setStockCategory("");
  };

  const handleCreateTestUsers = async () => {
    const emails = testEmails
      .split(/[\n,]/)
      .map((e) => e.trim())
      .filter(Boolean);

    if (emails.length === 0) return;

    const payload = await makeRequest("admin/test-users", "POST", { emails }, true, "admin_token");
    if (payload.detail) {
      showMessage(payload.detail.message || "Request failed", true);
      return;
    }

    setTestUsersResult(payload as { created: string[]; skipped: string[]; password: string });
    showMessage(`Created ${payload.created.length} test user(s)`);
  };

  const inputClass =
    "px-3 py-2 rounded-full bg-white/20 text-white placeholder-gray-300 outline-none border border-white/10 focus:ring-2 focus:ring-green-400/70";
  const buttonClass =
    "px-5 py-2 rounded-full bg-gradient-to-r from-[#6ee38f] to-[#3ca76a] text-white font-medium hover:opacity-90 transition";

  return (
    <div className="max-w-[600px] mx-auto mt-[4rem] px-6 text-white space-y-10">
      <h1 className="text-3xl font-semibold">Admin Panel</h1>

      <section className="space-y-3">
        <h2 className="text-xl font-medium">Verify user</h2>
        <div className="flex gap-3">
          <input
            className={inputClass}
            placeholder="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <button className={buttonClass} onClick={() => call(`user/verify/${username}`, "PUT")}>
            Verify
          </button>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-medium">Stock provider</h2>
        <div className="flex gap-3">
          <button className={buttonClass} onClick={() => call("stocks/", "POST")}>
            Start
          </button>
          <button className={buttonClass} onClick={() => call("stocks/", "DELETE")}>
            Stop
          </button>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-medium">Create stock</h2>
        <p className="text-sm text-gray-300">
          The stock provider only updates stocks that already exist — create at least one before
          starting it, or the stocks page stays empty.
        </p>
        <div className="flex gap-3 flex-wrap">
          <input
            className={inputClass}
            placeholder="name"
            value={stockName}
            onChange={(e) => setStockName(e.target.value)}
          />
          <input
            className={inputClass}
            placeholder="category"
            value={stockCategory}
            onChange={(e) => setStockCategory(e.target.value)}
          />
          <input
            className={inputClass}
            placeholder="starting value"
            value={stockValue}
            onChange={(e) => setStockValue(e.target.value)}
          />
          <button className={buttonClass} onClick={handleCreateStock}>
            Create
          </button>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-medium">Create test users</h2>
        <p className="text-sm text-gray-300">
          Enter one email/username per line (or comma-separated). Each will be created as a
          verified regular user with a shared default password, for testing login.
        </p>
        <textarea
          className={inputClass + " w-full rounded-2xl"}
          rows={4}
          placeholder={"tester1@example.com\ntester2@example.com"}
          value={testEmails}
          onChange={(e) => setTestEmails(e.target.value)}
        />
        <button className={buttonClass} onClick={handleCreateTestUsers}>
          Create
        </button>

        {testUsersResult && (
          <div className="text-sm space-y-1 bg-white/10 rounded-2xl p-4">
            <p>
              Password for all test users: <span className="font-mono">{testUsersResult.password}</span>
            </p>
            <p>Created: {testUsersResult.created.join(", ") || "none"}</p>
            <p>Already existed (skipped): {testUsersResult.skipped.join(", ") || "none"}</p>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-medium">Broadcast news</h2>
        <div className="flex gap-3">
          <input
            className={inputClass + " flex-1"}
            placeholder="message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <button className={buttonClass} onClick={() => call("news/", "POST", { message })}>
            Broadcast
          </button>
        </div>
      </section>
    </div>
  );
};

const AdminPage = () => {
  const [loggedIn, setLoggedIn] = useState(() => !!localStorage.getItem("admin_token"));
  return loggedIn ? <AdminPanel /> : <AdminLogin onSuccess={() => setLoggedIn(true)} />;
};

export default AdminPage;

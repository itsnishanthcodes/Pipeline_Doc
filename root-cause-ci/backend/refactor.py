import sys

with open(r'd:\Projects\Pipeline_Doc\root-cause-ci\frontend\src\components\DashboardWorkspace.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Add Lucide imports
code = code.replace("import { postGitHubWebhook", "import { BookMarked, Search, History, LogOut, Settings, Github, CheckCircle, Copy, Terminal, Wrench } from 'lucide-react';\nimport { postGitHubWebhook")

# Replace header and tabs
old_header = '''    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header glass-card">
        <div className="user-welcome-group">
          <div className="user-avatar">{user.full_name.charAt(0)}</div>
          <div>
            <h2>Developer CI Workspace</h2>
            <p className="user-email-badge">
              Logged in as: <strong>{user.email}</strong> • Role: <strong>{user.role}</strong>
              {user.github_username && <span className="gh-tag"> • @{user.github_username}</span>}
            </p>
          </div>
        </div>

        <div className="dashboard-actions" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button className="btn-secondary" onClick={onOpenProfile} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            ⚙️ Profile & Credentials
          </button>
          <button className="btn-secondary" onClick={onLogout}>
            Sign Out
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="dashboard-nav-tabs">
        <button
          className={`dash-tab ${activeTab === 'repositories' ? 'active' : ''}`}
          onClick={() => setActiveTab('repositories')}
        >
          📚 Repositories
        </button>
        <button
          className={`dash-tab ${activeTab === 'github_analysis' ? 'active' : ''}`}
          onClick={() => setActiveTab('github_analysis')}
        >
          🔍 GitHub Pipeline Analysis
        </button>
        <button
          className={`dash-tab ${activeTab === 'runs' ? 'active' : ''}`}
          onClick={() => setActiveTab('runs')}
        >
          📊 Ingestion History ({ingestedRuns.length})
        </button>
      </div>'''

new_header = '''    <div className="dashboard-layout">
      <aside className="dashboard-sidebar">
        <div style={{ padding: '0 16px 20px', display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px solid var(--border-glass)', marginBottom: '10px' }}>
          <div className="user-avatar" style={{ width: '40px', height: '40px', fontSize: '1.2rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{user.full_name.charAt(0)}</div>
          <div style={{ overflow: 'hidden' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-main)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{user.full_name}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{user.email}</div>
          </div>
        </div>

        <button className={`sidebar-nav-item ${activeTab === 'repositories' ? 'active' : ''}`} onClick={() => setActiveTab('repositories')}>
          <BookMarked size={18} />
          Repositories
        </button>
        <button className={`sidebar-nav-item ${activeTab === 'github_analysis' ? 'active' : ''}`} onClick={() => setActiveTab('github_analysis')}>
          <Search size={18} />
          Pipeline Analysis
        </button>
        <button className={`sidebar-nav-item ${activeTab === 'runs' ? 'active' : ''}`} onClick={() => setActiveTab('runs')}>
          <History size={18} />
          History ({ingestedRuns.length})
        </button>

        <div style={{ flex: 1 }} />
        <button className="sidebar-nav-item" onClick={onOpenProfile}>
          <Settings size={18} />
          Settings
        </button>
        <button className="sidebar-nav-item" onClick={onLogout} style={{ color: 'var(--accent-red)' }}>
          <LogOut size={18} />
          Sign Out
        </button>
      </aside>
      <main className="dashboard-content-area">'''

code = code.replace(old_header, new_header)

# Replace closing tags
old_footer = '''      )}
    </div>
  );
};'''
new_footer = '''      )}
      </main>
    </div>
  );
};'''
code = code.replace(old_footer, new_footer)

# Replace Emojis
code = code.replace("🟢 HEALTHY (PASSED)", "HEALTHY (PASSED)")
code = code.replace("🔍 Deterministic Evidence Chain", "<span style={{display:'flex', alignItems:'center', gap:'6px'}}><Search size={16}/> Deterministic Evidence Chain</span>")
code = code.replace("🤖 Constrained AI Root Cause Summary", "<span style={{display:'flex', alignItems:'center', gap:'6px'}}><Terminal size={16}/> Constrained AI Root Cause Summary</span>")
code = code.replace("🛠️ Proposed Fix (Constrained Scope)", "<span style={{display:'flex', alignItems:'center', gap:'6px'}}><Wrench size={16}/> Proposed Fix (Constrained Scope)</span>")
code = code.replace("🚀 Create Fix PR on GitHub", "<span style={{display:'flex', alignItems:'center', gap:'6px'}}><Github size={16}/> Create Fix PR</span>")
code = code.replace("✅ Pull Request Created!", "<span style={{display:'flex', alignItems:'center', gap:'6px'}}><CheckCircle size={16}/> Pull Request Created!</span>")
code = code.replace("✅ Copied to Clipboard!", "<span style={{display:'flex', alignItems:'center', gap:'4px'}}><CheckCircle size={14}/> Copied!</span>")
code = code.replace("📋 Copy Report", "<span style={{display:'flex', alignItems:'center', gap:'4px'}}><Copy size={14}/> Copy Report</span>")

# Add Page Headers
code = code.replace('''<div className="glass-card" style={{ width: '100%' }}>
            <h3>Connected GitHub Repositories (CI/CD Enabled)</h3>
            <p className="subtitle">These repositories have GitHub Actions workflows configured.</p>''', '''<div className="page-header">
            <h2><BookMarked size={28} style={{ color: 'var(--accent-indigo)' }}/> Repositories</h2>
            <p>Manage and analyze your connected GitHub repositories with active workflows.</p>
          </div>
          <div className="glass-card" style={{ width: '100%' }}>''')

code = code.replace('''<div className="runs-list-panel glass-card">
            <h3>Backend Ingestion Stream</h3>
            <p className="subtitle">Real responses returned from FastAPI services</p>''', '''<div className="page-header" style={{ gridColumn: '1 / -1' }}>
            <h2><History size={28} style={{ color: 'var(--accent-indigo)' }}/> Ingestion History</h2>
            <p>Real-time stream of pipeline failures analyzed by the Root Cause CI engine.</p>
          </div>
          <div className="runs-list-panel glass-card">''')

code = code.replace('''<div className="glass-card trigger-panel">
          <h3>Analyze GitHub Pipeline Failure</h3>
          <p className="subtitle">
            Fetch pipeline logs from GitHub, classify the root cause, and optionally post an automated analysis report to the relevant Pull Request.
          </p>''', '''<div className="page-header">
            <h2><Search size={28} style={{ color: 'var(--accent-indigo)' }}/> Pipeline Analysis</h2>
            <p>Fetch pipeline logs, classify root causes, and generate automated fix pull requests.</p>
          </div>
          <div className="glass-card trigger-panel">
            <h3>Analyze GitHub Pipeline Failure</h3>
            <p className="subtitle">
              Fetch pipeline logs from GitHub, classify the root cause, and optionally post an automated analysis report to the relevant Pull Request.
            </p>''')

with open(r'd:\Projects\Pipeline_Doc\root-cause-ci\frontend\src\components\DashboardWorkspace.tsx', 'w', encoding='utf-8') as f:
    f.write(code)


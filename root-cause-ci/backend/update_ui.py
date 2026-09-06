
import sys

# Read the file
with open(r'd:\Projects\Pipeline_Doc\root-cause-ci\frontend\src\components\DashboardWorkspace.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Add Lucide imports
lucide_imports = '''import { BookMarked, Search, History, LogOut, Settings, Github, CheckCircle, XCircle, ChevronRight, Copy, Terminal, Wrench } from 'lucide-react';\n'''
code = code.replace('''import { postGitHubWebhook''', lucide_imports + '''import { postGitHubWebhook''')

# Update dashboard container to use layout
new_layout = '''<div className=\
dashboard-layout\>
      <aside className=\dashboard-sidebar\>
        <div style={{ padding: '0 16px 20px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className=\user-avatar\ style={{ width: '40px', height: '40px', fontSize: '1.2rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{user.full_name.charAt(0)}</div>
          <div style={{ overflow: 'hidden' }}>
            <div style={{ fontWeight: 600, color: 'white', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{user.full_name}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{user.email}</div>
          </div>
        </div>

        <button className={sidebar-nav-item } onClick={() => setActiveTab('repositories')}>
          <BookMarked size={18} />
          Repositories
        </button>
        <button className={sidebar-nav-item } onClick={() => setActiveTab('github_analysis')}>
          <Search size={18} />
          Pipeline Analysis
        </button>
        <button className={sidebar-nav-item } onClick={() => setActiveTab('runs')}>
          <History size={18} />
          History ({ingestedRuns.length})
        </button>

        <div style={{ flex: 1 }} />
        <button className=\sidebar-nav-item\ onClick={onOpenProfile}>
          <Settings size={18} />
          Settings
        </button>
        <button className=\sidebar-nav-item\ onClick={onLogout} style={{ color: 'var(--accent-red)' }}>
          <LogOut size={18} />
          Sign Out
        </button>
      </aside>
      <main className=\dashboard-content-area\>'''

code = code.replace('''<div className=\dashboard-container\>''', new_layout)

# Remove the old header and tabs
start_idx = code.find('''      {/* Header */}''')
end_idx = code.find('''      {/* Tab 1: Repositories */}''')
if start_idx != -1 and end_idx != -1:
    code = code[:start_idx] + code[end_idx:]

# Close the main tag at the end
code = code.replace('''    </div>\n  );\n};''', '''    </main>\n    </div>\n  );\n};''')

# Clean up emojis
code = code.replace('''🟢 HEALTHY (PASSED)''', '''HEALTHY (PASSED)''')
code = code.replace('''🔍 Deterministic Evidence Chain''', '''<Search size={16} style={{display:'inline', verticalAlign:'text-bottom', marginRight:'6px'}}/> Deterministic Evidence Chain''')
code = code.replace('''🤖 Constrained AI Root Cause Summary''', '''<Terminal size={16} style={{display:'inline', verticalAlign:'text-bottom', marginRight:'6px'}}/> Constrained AI Root Cause Summary''')
code = code.replace('''🛠️ Proposed Fix (Constrained Scope)''', '''<Wrench size={16} style={{display:'inline', verticalAlign:'text-bottom', marginRight:'6px'}}/> Proposed Fix (Constrained Scope)''')
code = code.replace('''🚀 Create Fix PR on GitHub''', '''<Github size={16} style={{display:'inline', verticalAlign:'text-bottom', marginRight:'6px'}}/> Create Fix PR''')
code = code.replace('''✅ Pull Request Created!''', '''<CheckCircle size={16} style={{display:'inline', verticalAlign:'text-bottom', marginRight:'6px'}}/> Pull Request Created!''')
code = code.replace('''✅ Copied to Clipboard!''', '''<CheckCircle size={14} style={{display:'inline', verticalAlign:'text-bottom', marginRight:'4px'}}/> Copied!''')
code = code.replace('''📋 Copy Report''', '''<Copy size={14} style={{display:'inline', verticalAlign:'text-bottom', marginRight:'4px'}}/> Copy Report''')

with open(r'd:\Projects\Pipeline_Doc\root-cause-ci\frontend\src\components\DashboardWorkspace.tsx', 'w', encoding='utf-8') as f:
    f.write(code)


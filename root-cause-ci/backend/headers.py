
with open(r'd:\Projects\Pipeline_Doc\root-cause-ci\frontend\src\components\DashboardWorkspace.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
'''          <div className=\
glass-card\ style={{ width: '100%' }}>\n            <h3>Connected GitHub Repositories (CI/CD Enabled)</h3>\n            <p className=\subtitle\>These repositories have GitHub Actions workflows configured.</p>''',
'''          <div className=\page-header\>\n            <h2><BookMarked size={28} style={{ color: 'var(--accent-indigo)' }}/> Repositories</h2>\n            <p>Manage and analyze your connected GitHub repositories with active workflows.</p>\n          </div>\n          <div className=\glass-card\ style={{ width: '100%' }}>'''
)

code = code.replace(
'''          <div className=\runs-list-panel
glass-card\>\n            <h3>Backend Ingestion Stream</h3>\n            <p className=\subtitle\>Real responses returned from FastAPI services</p>''',
'''          <div className=\page-header\ style={{ gridColumn: '1 / -1' }}>\n            <h2><History size={28} style={{ color: 'var(--accent-indigo)' }}/> Ingestion History</h2>\n            <p>Real-time stream of pipeline failures analyzed by the Root Cause CI engine.</p>\n          </div>\n          <div className=\runs-list-panel
glass-card\>'''
)

code = code.replace(
'''        <div className=\glass-card
trigger-panel\>\n          <h3>Analyze GitHub Pipeline Failure</h3>\n          <p className=\subtitle\>\n            Fetch pipeline logs from GitHub, classify the root cause, and optionally post an automated analysis report to the relevant Pull Request.\n          </p>''',
'''        <>\n          <div className=\page-header\>\n            <h2><Search size={28} style={{ color: 'var(--accent-indigo)' }}/> Pipeline Analysis</h2>\n            <p>Fetch pipeline logs, classify root causes, and generate automated fix pull requests.</p>\n          </div>\n          <div className=\glass-card
trigger-panel\>'''
)

code = code.replace('''          )}\n        </div>\n      </main>''', '''          )}\n        </div>\n        </>\n      </main>''')

with open(r'd:\Projects\Pipeline_Doc\root-cause-ci\frontend\src\components\DashboardWorkspace.tsx', 'w', encoding='utf-8') as f:
    f.write(code)


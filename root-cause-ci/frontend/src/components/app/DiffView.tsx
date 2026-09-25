interface Line {
  kind: 'add' | 'del' | 'ctx' | 'hunk';
  text: string;
  oldNo?: number;
  newNo?: number;
}

function parse(diff: string): Line[] {
  const out: Line[] = [];
  let oldNo = 0;
  let newNo = 0;
  for (const raw of diff.split('\n')) {
    if (raw.startsWith('---') || raw.startsWith('+++')) continue;
    const hunk = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$/.exec(raw);
    if (hunk) {
      oldNo = Number(hunk[1]);
      newNo = Number(hunk[2]);
      out.push({ kind: 'hunk', text: raw });
    } else if (raw.startsWith('+')) {
      out.push({ kind: 'add', text: raw.slice(1), newNo: newNo++ });
    } else if (raw.startsWith('-')) {
      out.push({ kind: 'del', text: raw.slice(1), oldNo: oldNo++ });
    } else if (raw.length > 0 || out.length > 0) {
      out.push({ kind: 'ctx', text: raw.startsWith(' ') ? raw.slice(1) : raw, oldNo: oldNo++, newNo: newNo++ });
    }
  }
  while (out.length && out[out.length - 1].kind === 'ctx' && out[out.length - 1].text === '') out.pop();
  return out;
}

export function DiffView({ diff, file }: { diff: string; file: string }) {
  const lines = parse(diff);
  const added = lines.filter((l) => l.kind === 'add').length;
  const removed = lines.filter((l) => l.kind === 'del').length;
  return (
    <div className="diff">
      <div className="diff-head">
        <code className="diff-file">{file}</code>
        <span className="small"><span className="text-pass">+{added}</span> <span className="text-fail">-{removed}</span></span>
      </div>
      <div className="diff-scroll">
        <table className="diff-table">
          <tbody>
            {lines.map((l, i) => (
              <tr key={i} className={`diff-${l.kind}`}>
                {l.kind === 'hunk' ? (
                  <td colSpan={3} className="diff-hunk-text">{l.text}</td>
                ) : (
                  <>
                    <td className="diff-no" aria-hidden="true">{l.oldNo ?? ''}</td>
                    <td className="diff-no" aria-hidden="true">{l.newNo ?? ''}</td>
                    <td className="diff-code">
                      <span className="diff-sign" aria-hidden="true">{l.kind === 'add' ? '+' : l.kind === 'del' ? '-' : ' '}</span>
                      {l.kind !== 'ctx' && <span className="sr-only">{l.kind === 'add' ? 'added: ' : 'removed: '}</span>}
                      {l.text || ' '}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

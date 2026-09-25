import { Link } from 'react-router-dom';

export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true" className="logo-mark">
      <path d="M3 16h26" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.45" />
      <circle cx="6" cy="16" r="3" fill="currentColor" opacity="0.55" />
      <circle cx="26" cy="16" r="3" fill="var(--fail)" />
      <circle cx="16" cy="16" r="3.4" fill="var(--accent)" />
      <circle cx="16" cy="16" r="7.5" stroke="var(--accent)" strokeWidth="1.6" strokeDasharray="3.2 2.6" />
    </svg>
  );
}

export function Logo({ to = '/' }: { to?: string }) {
  return (
    <Link to={to} className="logo" aria-label="Root Cause CI home">
      <LogoMark />
      <span>Root Cause CI</span>
    </Link>
  );
}

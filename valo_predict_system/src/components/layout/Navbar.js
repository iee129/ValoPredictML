'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import styles from './Navbar.module.css';

const NAV_LINKS = [
  { href: '/', label: '홈' },
  { href: '/predict', label: '승률 예측' },
  { href: '/analytics', label: '통계 분석' },
  { href: '/history', label: '예측 기록' },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className={styles.nav}>
      <div className={styles.logo}>
        <span className={styles.logoAccent}>VALO</span>
        <span className={styles.logoText}>PredictML</span>
      </div>
      <div className={styles.links}>
        {NAV_LINKS.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`${styles.link} ${pathname === href ? styles.linkActive : ''}`}
          >
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}

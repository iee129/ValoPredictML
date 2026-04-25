import './globals.css';
import styles from './layout.module.css';
import Navbar from '@/components/layout/Navbar';

export const metadata = {
  title: 'ValoPredictML — 발로란트 팀 조합 승률 예측',
  description: '발로란트 팀 조합을 입력하면 AI가 승리 확률을 예측합니다.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body className={styles.root}>
        <Navbar />
        <main className={styles.main}>{children}</main>
      </body>
    </html>
  );
}

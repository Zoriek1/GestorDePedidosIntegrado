import { ReactNode } from 'react';
import { useAnimateOnMount } from '../../../hooks/useAnimateOnMount';
import styles from './StatsCard.module.css';

export interface StatsCardProps {
  title: string;
  value: ReactNode;
  icon: ReactNode;
  index: number; // Para calcular delay de animação
}

export function StatsCard({ title, value, icon, index }: StatsCardProps) {
  // Delay baseado no index: 0ms, 100ms, 200ms, etc.
  const animationDelay = index * 100;
  const animationClass = useAnimateOnMount('fadeInUp', animationDelay);

  return (
    <div className={`${styles.card} ${animationClass}`}>
      <div className={styles.cardBorderTop} />
      <div className={styles.cardContent}>
        <div className={styles.cardIcon}>{icon}</div>
        <div className={styles.cardTitle}>{title}</div>
        <div className={styles.cardValue}>{value}</div>
      </div>
    </div>
  );
}

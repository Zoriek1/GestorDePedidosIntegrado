import { ReactNode } from 'react';
import { useAnimateOnMount } from '../../../hooks/useAnimateOnMount';
import styles from './StatsCard.module.css';

export interface StatsCardProps {
  title: string;
  value: ReactNode;
  helperText?: string;
  icon: ReactNode;
  index?: number;
  iconBg?: string;
  iconColor?: string;
}

export function StatsCard({ title, value, helperText, icon, index = 0, iconBg, iconColor }: StatsCardProps) {
  const animationDelay = index * 100;
  const animationClass = useAnimateOnMount('fadeInUp', animationDelay);

  return (
    <div className={`${styles.card} ${animationClass}`}>
      <div className={styles.cardBorderTop} />
      <div className={styles.cardContent}>
        <div
          className={styles.cardIcon}
          style={iconBg ? { background: iconBg, color: iconColor } : undefined}
        >
          {icon}
        </div>
        <div className={styles.cardTitle}>{title}</div>
        <div className={styles.cardValue}>{value}</div>
        {helperText && <div className={styles.cardTitle} style={{ textTransform: 'none', letterSpacing: 0 }}>{helperText}</div>}
      </div>
    </div>
  );
}

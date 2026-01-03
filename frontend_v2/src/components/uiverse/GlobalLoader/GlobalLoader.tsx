import { useIsFetching } from '@tanstack/react-query';
import styles from './GlobalLoader.module.css';

export function GlobalLoader() {
  const isFetching = useIsFetching() > 0;

  if (!isFetching) {
    return null;
  }

  return (
    <div className={styles.loader}>
      <div className={styles.circle}>
        <div className={styles.dot} />
        <div className={styles.outline} />
      </div>
      <div className={styles.circle}>
        <div className={styles.dot} />
        <div className={styles.outline} />
      </div>
      <div className={styles.circle}>
        <div className={styles.dot} />
        <div className={styles.outline} />
      </div>
      <div className={styles.circle}>
        <div className={styles.dot} />
        <div className={styles.outline} />
      </div>
    </div>
  );
}

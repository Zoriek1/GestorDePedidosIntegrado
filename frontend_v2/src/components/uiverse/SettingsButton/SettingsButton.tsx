import styles from './SettingsButton.module.css';

export interface SettingsButtonProps {
  onClick: () => void;
  'aria-label'?: string;
}

export function SettingsButton({ onClick, 'aria-label': ariaLabel = 'Criar pedido' }: SettingsButtonProps) {
  return (
    <button
      className={styles.addButton}
      onClick={onClick}
      aria-label={ariaLabel}
      type="button"
    >
      <div className={styles.plusIcon} />
    </button>
  );
}

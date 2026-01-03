import { forwardRef } from 'react';
import styles from './MinimalCheckbox.module.css';

export interface MinimalCheckboxProps {
  checked: boolean;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  id?: string;
  name?: string;
  'aria-label'?: string;
}

export const MinimalCheckbox = forwardRef<HTMLInputElement, MinimalCheckboxProps>(
  ({ checked, onChange, id, name, 'aria-label': ariaLabel }, ref) => {
    return (
      <label className={styles.container} htmlFor={id}>
        <input
          ref={ref}
          type="checkbox"
          id={id}
          name={name}
          checked={checked}
          onChange={onChange}
          aria-label={ariaLabel}
        />
        <span className={styles.checkbox}>
          <span className={styles.checkmark} />
        </span>
      </label>
    );
  }
);

MinimalCheckbox.displayName = 'MinimalCheckbox';

import React from 'react';
import styles from './FancyCheckbox.module.css';

export interface FancyCheckboxProps {
  checked: boolean;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  id?: string;
  name?: string;
  'aria-label'?: string;
}

export function FancyCheckbox({
  checked,
  onChange,
  id,
  name,
  'aria-label': ariaLabel,
}: FancyCheckboxProps) {
  return (
    <label className={styles.container} htmlFor={id}>
      <input
        type="checkbox"
        id={id}
        name={name}
        checked={checked}
        onChange={onChange}
        aria-label={ariaLabel}
      />
      <div className={styles.checkmark} />
    </label>
  );
}

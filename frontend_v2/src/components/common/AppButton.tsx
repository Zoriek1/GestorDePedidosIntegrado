/**
 * AppButton Component
 * Standardized button with consistent styling and loading states
 */

import { Button, ButtonProps, CircularProgress } from '@mui/material';
import { forwardRef } from 'react';

export interface AppButtonProps extends Omit<ButtonProps, 'textTransform'> {
  loading?: boolean;
}

export const AppButton = forwardRef<HTMLButtonElement, AppButtonProps>(
  ({ loading, children, disabled, sx, ...props }, ref) => {
    return (
      <Button
        ref={ref}
        {...props}
        disabled={disabled || loading}
        sx={{
          minHeight: '44px', // Mobile touch target
          textTransform: 'none', // Don't capitalize text
          ...sx,
        }}
      >
        {loading && (
          <CircularProgress
            size={20}
            sx={{
              mr: 1,
            }}
          />
        )}
        {children}
      </Button>
    );
  }
);

AppButton.displayName = 'AppButton';


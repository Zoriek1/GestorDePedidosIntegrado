/**
 * CopyOnClick component
 * Reusable component that copies text to clipboard on click/tap
 * Provides visual feedback and accessibility support
 */

import { useState, useCallback } from 'react';
import { Box, Tooltip } from '@mui/material';
import { copyToClipboard } from '../../lib/utils/clipboard';

interface CopyOnClickProps {
  textToCopy: string;
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
  successDurationMs?: number;
}

export function CopyOnClick({
  textToCopy,
  children,
  className,
  disabled = false,
  successDurationMs = 1200,
}: CopyOnClickProps) {
  const [copied, setCopied] = useState(false);
  const [tooltipOpen, setTooltipOpen] = useState(false);

  const isDisabled = disabled || !textToCopy || textToCopy.trim() === '';

  const handleCopy = useCallback(async () => {
    if (isDisabled) return;

    const success = await copyToClipboard(textToCopy);
    if (success) {
      setCopied(true);
      setTooltipOpen(true);
      setTimeout(() => {
        setCopied(false);
        setTooltipOpen(false);
      }, successDurationMs);
    }
  }, [textToCopy, isDisabled, successDurationMs]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (isDisabled) return;
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        e.stopPropagation();
        handleCopy();
      }
    },
    [handleCopy, isDisabled]
  );

  const tooltipText = copied ? 'Copiado!' : 'Clique para copiar';
  const ariaLabel = copied ? 'Copiado para a área de transferência' : 'Copiar para a área de transferência';

  return (
    <Tooltip
      title={tooltipText}
      open={tooltipOpen || undefined}
      onOpen={() => !copied && setTooltipOpen(true)}
      onClose={() => !copied && setTooltipOpen(false)}
      arrow
    >
      <Box
        component="div"
        role="button"
        tabIndex={isDisabled ? -1 : 0}
        aria-label={ariaLabel}
        onClick={handleCopy}
        onKeyDown={handleKeyDown}
        className={className}
        sx={{
          cursor: isDisabled ? 'default' : 'pointer',
          userSelect: 'none',
          transition: 'background-color 0.2s',
          '&:hover': isDisabled
            ? {}
            : {
                backgroundColor: 'action.hover',
              },
          '&:focus-visible': isDisabled
            ? {}
            : {
                outline: '2px solid',
                outlineColor: 'primary.main',
                outlineOffset: '2px',
              },
        }}
      >
        {children}
      </Box>
    </Tooltip>
  );
}

/**
 * Clipboard utility with fallback support
 * Uses modern Clipboard API with fallback to execCommand for older browsers
 */

<<<<<<< HEAD
=======
import { createLogger } from '../logger';

const log = createLogger('clipboard');

>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
/**
 * Copies text to clipboard
 * @param text - Text to copy
 * @returns Promise that resolves to true if successful, false otherwise
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (!text || text.trim() === '') {
    return false;
  }

  // Try modern Clipboard API first
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      // Fall through to fallback method
<<<<<<< HEAD
      console.warn('Clipboard API failed, trying fallback:', err);
=======
      log.warn('Clipboard API failed, trying fallback:', err);
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
    }
  }

  // Fallback: create temporary textarea and use execCommand
  try {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-999999px';
    textarea.style.top = '-999999px';
    textarea.setAttribute('readonly', '');
    document.body.appendChild(textarea);
    
    // Select and copy
    textarea.select();
    textarea.setSelectionRange(0, text.length);
    
    const successful = document.execCommand('copy');
    document.body.removeChild(textarea);
    
    return successful;
  } catch (err) {
<<<<<<< HEAD
    console.error('Fallback clipboard copy failed:', err);
=======
    log.error('Fallback clipboard copy failed:', err);
>>>>>>> cc8c9d5527969b86d44bbf8a302e541906c0fa14
    return false;
  }
}

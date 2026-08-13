/**
 * Utility function to strip emojis and other non-professional characters from text.
 */
export function stripEmojis(text: string | undefined | null): string {
  if (!text) return '';
  
  // Regex to match emojis and extended pictographic symbols
  const emojiRegex = /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{1FAB0}-\u{1FABF}\u{1FAC0}-\u{1FACF}\u{1FAD0}-\u{1FADF}\u{1FAE0}-\u{1FAEF}\u{1FAF0}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{2300}-\u{23FF}\u{2B50}\u{1F004}-\u{1F0CF}\u{1F170}-\u{1F251}]/gu;
  
  // Replace emojis and excessive whitespace
  return text
    .replace(emojiRegex, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

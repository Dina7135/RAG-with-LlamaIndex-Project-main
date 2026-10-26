# UI Guidelines

## RTL Support
- All Hebrew screens must use RTL (Right-to-Left) layout
- Code paths and API endpoints should remain in English/LTR
- Mixed content (Hebrew + English) should maintain proper directionality

## Design Rules
- Primary color: Blue (#3B82F6)
- Secondary color: Gray (#6B7280)
- Font: Inter for English, Rubik for Hebrew
- Spacing: 4px grid system

## Component Guidelines
- All buttons must have consistent padding
- Form inputs should have clear labels
- Error messages must be in red and clearly visible
- Success messages should be green and dismissible

## Accessibility
- All images must have alt text
- Keyboard navigation must be supported
- Color contrast ratio must meet WCAG AA standards
- Screen reader compatibility is required

## Performance
- Lazy load images below the fold
- Minimize bundle size through code splitting
- Use caching for API responses
- Optimize images for web delivery

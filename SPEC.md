# Resume Website Specification

## Project Overview
- **Project Name**: Personal Resume Portfolio
- **Type**: Single-page resume website
- **Core Functionality**: Showcase professional profile, experience, skills, projects, and contact information with smooth navigation
- **Target Users**: Recruiters, hiring managers, potential collaborators

---

## UI/UX Specification

### Layout Structure

**Sections (in order):**
1. **Hero** - Full viewport height, name, title, tagline, CTA button
2. **About** - Brief bio, profile image placeholder, key highlights
3. **Experience** - Timeline-style work history
4. **Skills** - Categorized skill cards with visual indicators
5. **Projects** - Grid of project cards with descriptions and links
6. **Contact** - Contact form (visual only), social links, footer

**Responsive Breakpoints:**
- Mobile: < 768px (single column)
- Tablet: 768px - 1024px (2 columns where applicable)
- Desktop: > 1024px (full layout)

### Visual Design

**Color Palette:**
- Background Primary: `#0a0a0f` (deep dark)
- Background Secondary: `#12121a` (card backgrounds)
- Background Tertiary: `#1a1a24` (hover states)
- Text Primary: `#e8e8ed` (main text)
- Text Secondary: `#8b8b9a` (muted text)
- Accent Primary: `#14b8a6` (teal - highlights, buttons)
- Accent Secondary: `#8b5cf6` (violet - gradients, borders)
- Accent Gradient: `linear-gradient(135deg, #14b8a6 0%, #8b5cf6 100%)`

**Typography:**
- Headings: "Clash Display", sans-serif (from CDN)
- Body: "Satoshi", sans-serif (from CDN)
- Font Sizes:
  - H1 (Hero): 4rem (desktop), 2.5rem (mobile)
  - H2 (Section): 2.5rem (desktop), 1.75rem (mobile)
  - H3 (Card titles): 1.25rem
  - Body: 1rem
  - Small: 0.875rem

**Spacing System:**
- Section padding: 100px vertical (desktop), 60px (mobile)
- Card padding: 24px
- Gap between cards: 24px
- Container max-width: 1200px

**Visual Effects:**
- Cards: subtle border with `rgba(139, 92, 246, 0.15)`, glow on hover
- Buttons: gradient background, scale(1.02) on hover
- Section titles: gradient text effect
- Smooth scroll behavior
- Fade-in-up animations on scroll

### Components

**Navigation:**
- Fixed top navigation bar
- Transparent → solid background on scroll
- Logo/name on left, nav links on right
- Mobile: hamburger menu

**Hero Section:**
- Centered content
- Animated gradient text for name
- Subtitle with typing effect
- "View Work" CTA button with arrow icon

**Experience Timeline:**
- Vertical line on left (desktop) / center (mobile)
- Alternating left/right cards (desktop)
- Date badges with accent color
- Company, role, duration, description

**Skill Cards:**
- Grid layout (3 columns desktop, 2 tablet, 1 mobile)
- Icon + skill name + proficiency bar
- Categories: Frontend, Backend, Tools

**Project Cards:**
- Image placeholder area
- Title, description, tech stack tags
- Links: Live demo, GitHub repo
- Hover: lift effect with shadow

**Contact Section:**
- Two-column layout (form + info)
- Form fields: Name, Email, Message
- Social icons row
- Footer with copyright

---

## Functionality Specification

### Core Features
1. **Smooth Scroll Navigation** - Click nav links to scroll to sections
2. **Scroll Animations** - Elements animate in when entering viewport
3. **Responsive Design** - Adapts to all screen sizes
4. **Interactive Elements** - Hover states, button animations
5. **Mobile Navigation** - Hamburger menu with slide-in drawer

### User Interactions
- Nav links → smooth scroll to section
- CTA button → scroll to Projects section
- Project cards → hover effect, clickable links
- Social icons → open in new tab
- Mobile menu toggle

### Animations
- Hero: fade-in-up on load (staggered)
- Sections: fade-in-up on scroll into view
- Cards: subtle lift + glow on hover
- Buttons: scale + color shift on hover
- Navigation: background fade on scroll

---

## Acceptance Criteria

1. ✅ All 6 sections visible and properly styled
2. ✅ Dark theme with teal/violet accents applied consistently
3. ✅ Smooth scroll works for all nav links
4. ✅ Responsive on mobile, tablet, desktop
5. ✅ Animations trigger on scroll
6. ✅ All hover states functional
7. ✅ Navigation fixed and functional
8. ✅ No horizontal scroll on any viewport
9. ✅ All fonts load correctly
10. ✅ Clean, valid HTML structure

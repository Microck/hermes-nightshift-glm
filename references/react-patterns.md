# React Best-Practice Patterns

## Core Philosophy

From Dan Abramov's "You Might Not Need an Effect": Effects are a getaway hatch for synchronizing with external systems. Most effects can be eliminated by moving logic out of effects or into event handlers.

---

## Effect Anti-Patterns (useEffect)

### 1. Computing Derived State in Effect

**Anti-pattern:**
```js
const [name, setName] = useState('');
const [greeting, setGreeting] = useState('');

useEffect(() => {
  setGreeting(`Hello, ${name}!`);
}, [name]);
```

**Fix:** Use lazy initialization or derive during render:
```js
const [name, setName] = useState('');
const greeting = `Hello, ${name}!`; // derived, no state needed
```

**Rule:** If a value can be computed from existing state/props during render, it does not need its own state or effect.

---

### 2. Updating State Based on Props

**Anti-pattern:**
```js
function CountReset({ initial }) {
  const [count, setCount] = useState(initial);
  useEffect(() => {
    setCount(initial);
  }, [initial]);
}
```

**Fix:** Use a key to reset the component, or use `useEffect` only as a last resort:
```js
function CountReset({ initial }) {
  const [count, setCount] = useState(() => initial); // lazy init
  // Remove the effect entirely
}
```

**Rule:** Props are already reactive. Avoid syncing state with props via effect unless you intentionally want to preserve a stale value.

---

### 3. Event-Only Logic Inside Effect

**Anti-pattern:**
```js
useEffect(() => {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') submitForm();
  };
  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, []);
```

**Fix:** This is often fine IF it's truly side-effect logic. But if it's related to user interaction, consider if it belongs in an event handler instead.

---

### 4. Chained Effects (Effect triggers Effect)

**Anti-pattern:**
```js
useEffect(() => {
  fetchUser(userId).then(setUser);
}, [userId]);

useEffect(() => {
  if (user) fetchPermissions(user.id).then(setPermissions);
}, [user?.id]); // user is often stale here
```

**Fix:** Combine into one effect, or use a data-fetching library (React Query, SWR, etc.).

---

### 5. Missing Dependency Causing Stale Closure

**Anti-pattern:**
```js
const [count, setCount] = useState(0);
useEffect(() => {
  const id = setInterval(() => {
    console.log(count); // always 0 — stale closure
  }, 1000);
  return () => clearInterval(id);
}, []); // missing [count]
```

**Fix:** Add the dependency, or use a ref for mutable values:
```js
const countRef = useRef(count);
countRef.current = count;
useEffect(() => {
  const id = setInterval(() => {
    console.log(countRef.current); // always fresh
  }, 1000);
  return () => clearInterval(id);
}, []);
```

---

## Image Component Anti-Patterns

### 1. Missing Width/Height (Layout Shift)

**Anti-pattern:**
```jsx
<img src={src} alt="desc" />
```

**Fix:** Always provide explicit width/height OR use the CSS aspect-ratio property:
```jsx
<img src={src} alt="desc" width={800} height={600} />
// or
<div style={{ aspectRatio: '4/3' }}>
  <img src={src} alt="desc" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
</div>
```

### 2. Loading Full-Res Images on All Viewports

**Anti-pattern:**
```jsx
<img src="/hero-large.jpg" />
```

**Fix:** Use responsive images:
```jsx
<img srcSet="/hero-480.jpg 480w, /hero-1024.jpg 1024w" sizes="100vw" />
// or Next.js Image component
import Image from 'next/image';
<Image src="/hero.jpg" alt="Hero" fill sizes="100vw" />
```

### 3. No Loading/Error States

**Anti-pattern:**
```jsx
<img src={userAvatar} />
```

**Fix:** Handle loading and error states:
```jsx
const [loaded, setLoaded] = useState(false);
const [error, setError] = useState(false);
<img src={userAvatar} onLoad={() => setLoaded(true)} onError={() => setError(true)} />
```

### 4. Decorative Images Without Empty Alt

**Anti-pattern:**
```jsx
<img src="/decorative-bg.svg" />
```

**Fix:** If decorative, alt must be empty string:
```jsx
<img src="/decorative-bg.svg" alt="" aria-hidden="true" />
```

---

## React 19 / Next.js 15 Patterns

### Server Components

- Prefer Server Components (no "use client") for data fetching and static content
- Add "use client" only when you need browser APIs, event handlers, or hooks
- Keep Client Components as leaves in the component tree

### use() Hook for Promises

**Old:**
```js
// ❌ Wrong — fetching inside useEffect
useEffect(() => { fetchData().then(setData); }, []);
```

**New (React 19):**
```js
// ✅ New — await directly in Server Component or use() in Client Component
const data = use(fetchData());
```

---

## Detection Patterns (What to Search For)

| Anti-pattern | Search Pattern |
|---|---|
| Stale closure in interval | `setInterval` + `useEffect` + `[]` deps |
| Missing deps | `useEffect` without a dependency that appears in the callback |
| Derived state in effect | `useState` + `useEffect` + `setState` pattern |
| setState in useEffect for props | `useEffect.*set[A-Z]` + `props.` |
| No alt text | `<img` not followed by `alt=` |
| Layout shift risk | `<img` without `width` and `height` |
| Missing Image loading | Next.js `<Image` without `placeholder="blur"` for local images |

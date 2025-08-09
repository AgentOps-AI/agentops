# React Context Providers 🚀

Hey there! This folder is where all the React Context Providers for our dashboard app live.

## What are these "Providers" anyway? 🤔

Think of Providers as a cool way to send data (like user settings or the current theme) to many parts of our app without manually passing it down through every single component (we call this "prop drilling", and just like drilling for oil, it does more harm than good most of the time). It's like a global shortcut for data! You can also use something like Redux, MobX, or Zustand, but we're using Context API for this, it is simple, effective, and easy to understand.

They use React's Context API, and a typical setup involves three main parts:

1.  **Context Creation ✨**: We use `createContext` to make a new context object.
2.  **Provider Component 🎁**: This is a special component that takes `children` (other components) and uses `<Context.Provider>` to share the context value with everything inside it.
3.  **Custom Hook 🎣 (Optional but Super Handy!)**: Often, we create a custom hook (like `useMyCoolContext`) to make it super easy for other components to grab the data from the context.

## How to Use 'Em 🛠️

Using a provider is pretty straightforward:

1.  **Wrap it up!** 🌯 Take your Provider component and wrap it around the part of your app (or the whole thing!) that needs the data. This is usually done in a layout file or a main app component.
2.  **Grab the data!** 📲 In any component nested inside that Provider, you can now access the shared data using the custom hook (if you made one) or `useContext(MyContext)`.

## Example Time! Let's look at `SidebarProvider` 🧭

The `SidebarProvider` is a simple one that keeps track of whether our sidebar is open or closed.

**How it's built (`dashboard/app/providers/sidebar-provider.tsx`):**

```tsx
'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface SidebarContextType {
  isExpanded: boolean;
  setIsExpanded: (value: boolean) => void;
}

// 1. Context Creation ✨
export const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

// 3. Custom Hook 🎣
export function useSidebar() {
  const context = useContext(SidebarContext);
  if (context === undefined) {
    throw new Error('Oops! useSidebar must be used inside a SidebarProvider');
  }
  return context;
}

// 2. Provider Component 🎁
export function SidebarProvider({ children }: { children: ReactNode }) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Little bit of magic to remember the sidebar state even if you refresh the page!
  useEffect(() => {
    const savedState = localStorage.getItem('sidebarExpanded');
    if (savedState !== null) {
      setIsExpanded(savedState === 'true');
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('sidebarExpanded', isExpanded.toString());
  }, [isExpanded]);

  return (
    <SidebarContext.Provider value={{ isExpanded, setIsExpanded }}>
      {children}
    </SidebarContext.Provider>
  );
}
```

**How to use it in the app:**

First, you'd wrap a part of your app with `SidebarProvider` (maybe in `app/(with-layout)/layout.tsx`):

```tsx
// e.g., in app/(with-layout)/layout.tsx
import { SidebarProvider } from '@/app/providers/sidebar-provider';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      {/* ... other cool providers and layout stuff ... */}
      {children}
      {/* ... more layout stuff ... */}
    </SidebarProvider>
  );
}
```

Then, any component inside that can use the `useSidebar` hook to get the sidebar's state and change it:

```tsx
import { useSidebar } from '@/app/providers/sidebar-provider';

function MyAwesomeComponent() {
  const { isExpanded, setIsExpanded } = useSidebar();

  return (
    <button onClick={() => setIsExpanded(!isExpanded)}>
      {isExpanded ? 'Hide Sidebar 👇' : 'Show Sidebar 👉'}
    </button>
  );
}
```

## Making Your Own Provider? Awesome! 💡

1.  Pop a new `.tsx` file in this directory (e.g., `my-super-cool-provider.tsx`).
2.  Follow the pattern you see in the other providers:
    *   Define an `interface` for the data your context will hold.
    *   Use `createContext`.
    *   Build your Provider component.
    *   Make a sweet custom hook for easy access!
3.  Wrap the part of your app that needs it with your new Provider. You might add it to a layout file or group it with other providers if you have a central spot for them (like an `app/providers.tsx` file).

Happy coding! 🎉

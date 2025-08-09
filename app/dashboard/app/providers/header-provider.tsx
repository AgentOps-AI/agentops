'use client';

import { createContext, ReactNode, useContext, useState, useMemo } from 'react';

type HeaderContext = {
  headerNotification: boolean;
  setHeaderNotification: (value: boolean) => void;
  headerTitle: string;
  setHeaderTitle: (value: string) => void;
  headerContent: ReactNode;
  setHeaderContent: (value: ReactNode) => void;
};

/**
 * Context for managing dynamic content and notifications within the application header.
 */
const Context = createContext<HeaderContext | undefined>(undefined);

/**
 * Provider component for the header context.
 * Manages state for header notifications, title, and custom content.
 *
 * @param {object} props - The component props.
 * @param {ReactNode} props.children - The child components to render.
 * @returns {JSX.Element} The context provider wrapping children.
 */
export default function HeaderProvider({ children }: { children: ReactNode }) {
  const [headerNotification, setHeaderNotification] = useState<boolean>(false);
  const [headerTitle, setHeaderTitle] = useState<string>('');
  const [headerContent, setHeaderContent] = useState<ReactNode>(null);

  const contextValue = useMemo(
    () => ({
      headerNotification,
      setHeaderNotification,
      headerTitle,
      setHeaderTitle,
      headerContent,
      setHeaderContent,
    }),
    [headerNotification, headerTitle, headerContent],
  );

  return <Context.Provider value={contextValue}>{children}</Context.Provider>;
}

/**
 * Custom hook to access the header context.
 * Provides an error if used outside of a HeaderProvider.
 * @returns {HeaderContext} The header context, including notification state, title, custom content, and their setters.
 */
export const useHeaderContext = () => {
  const context = useContext(Context);

  if (context === undefined)
    throw new Error('HeaderComponent must be used within a HeaderProvider');

  return context;
};

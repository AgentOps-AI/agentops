'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface SidebarContextType {
  isExpanded: boolean;
  setIsExpanded: (value: boolean) => void;
}

/**
 * Context for managing the sidebar's expanded state.
 */
export const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

/**
 * Custom hook to access the sidebar context.
 * Provides an error if used outside of a SidebarProvider.
 * @returns {SidebarContextType} The sidebar context.
 */
export function useSidebar() {
  const context = useContext(SidebarContext);
  if (context === undefined) {
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
}

/**
 * Provider component for the sidebar context.
 * Manages the expanded state of the sidebar and persists it to localStorage.
 * @param {object} props - The component props.
 * @param {ReactNode} props.children - The child components to render.
 */
export function SidebarProvider({ children }: { children: ReactNode }) {
  const [isExpanded, setIsExpanded] = useState(true);

  // This loads the sidebar state from localStorage on mount
  useEffect(() => {
    try {
      const savedState = localStorage.getItem('sidebarExpanded');
      if (savedState !== null) {
        setIsExpanded(savedState === 'true');
      }
    } catch (error) {
      console.error('Error accessing localStorage:', error);
    }
  }, []);

  // This saves the sidebar state to localStorage when it changes
  useEffect(() => {
    try {
      localStorage.setItem('sidebarExpanded', isExpanded.toString());
    } catch (error) {
      console.error('Error writing to localStorage:', error);
    }
  }, [isExpanded]);

  return (
    <SidebarContext.Provider value={{ isExpanded, setIsExpanded }}>
      {children}
    </SidebarContext.Provider>
  );
}

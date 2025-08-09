'use client';

import React, { createContext, useContext, useReducer, ReactNode, useCallback } from 'react';

// Types
interface BillingState {
  // UI State
  expandedOrgId: string | null;
  selectedOrgForCheckout: string | null;
  showPricingForOrg: string | null;

  // Operation State
  processingOrgIds: Set<string>;
  confirmationState: {
    orgId: string;
    action: 'cancel' | 'reactivate' | null;
  };
  selectedAction: {
    orgId: string;
    action: 'update' | 'reactivate' | null;
  };

  // Checkout State
  clientSecret: string | null;
  isFetchingClientSecret: boolean;

  // Discount State
  validatedDiscountCode: string | null;
  validatedDiscountDescription: string | null;

  // Payment Processing State
  paymentProcessingOrgIds: Set<string>; // Orgs that have paid but waiting for webhook
}

type BillingAction =
  | { type: 'SET_EXPANDED_ORG'; payload: string | null }
  | { type: 'SET_SELECTED_ORG_FOR_CHECKOUT'; payload: string | null }
  | { type: 'SET_SHOW_PRICING'; payload: string | null }
  | { type: 'SET_PROCESSING'; payload: { orgId: string; isProcessing: boolean } }
  | {
      type: 'SET_CONFIRMATION_STATE';
      payload: { orgId: string; action: 'cancel' | 'reactivate' | null };
    }
  | {
      type: 'SET_SELECTED_ACTION';
      payload: { orgId: string; action: 'update' | 'reactivate' | null };
    }
  | { type: 'SET_CLIENT_SECRET'; payload: string | null }
  | { type: 'SET_FETCHING_CLIENT_SECRET'; payload: boolean }
  | { type: 'SET_DISCOUNT'; payload: { code: string | null; description: string | null } }
  | { type: 'SET_PAYMENT_PROCESSING'; payload: { orgId: string; isProcessing: boolean } }
  | { type: 'RESET_ORG_STATE'; payload: string }
  | { type: 'RESET_ALL' };

const initialState: BillingState = {
  expandedOrgId: null,
  selectedOrgForCheckout: null,
  showPricingForOrg: null,
  processingOrgIds: new Set(),
  confirmationState: { orgId: '', action: null },
  selectedAction: { orgId: '', action: null },
  clientSecret: null,
  isFetchingClientSecret: false,
  validatedDiscountCode: null,
  validatedDiscountDescription: null,
  paymentProcessingOrgIds: new Set(),
};

function billingReducer(state: BillingState, action: BillingAction): BillingState {
  switch (action.type) {
    case 'SET_EXPANDED_ORG':
      return { ...state, expandedOrgId: action.payload };

    case 'SET_SELECTED_ORG_FOR_CHECKOUT':
      return { ...state, selectedOrgForCheckout: action.payload };

    case 'SET_SHOW_PRICING':
      return { ...state, showPricingForOrg: action.payload };

    case 'SET_PROCESSING': {
      const newProcessingIds = new Set(state.processingOrgIds);
      if (action.payload.isProcessing) {
        newProcessingIds.add(action.payload.orgId);
      } else {
        newProcessingIds.delete(action.payload.orgId);
      }
      return { ...state, processingOrgIds: newProcessingIds };
    }

    case 'SET_CONFIRMATION_STATE':
      return { ...state, confirmationState: action.payload };

    case 'SET_SELECTED_ACTION':
      return { ...state, selectedAction: action.payload };

    case 'SET_CLIENT_SECRET':
      return { ...state, clientSecret: action.payload };

    case 'SET_FETCHING_CLIENT_SECRET':
      return { ...state, isFetchingClientSecret: action.payload };

    case 'SET_DISCOUNT':
      return {
        ...state,
        validatedDiscountCode: action.payload.code,
        validatedDiscountDescription: action.payload.description,
      };

    case 'SET_PAYMENT_PROCESSING': {
      const newPaymentProcessingIds = new Set(state.paymentProcessingOrgIds);
      if (action.payload.isProcessing) {
        newPaymentProcessingIds.add(action.payload.orgId);
      } else {
        newPaymentProcessingIds.delete(action.payload.orgId);
      }
      return { ...state, paymentProcessingOrgIds: newPaymentProcessingIds };
    }

    case 'RESET_ORG_STATE': {
      const newProcessingIds = new Set(state.processingOrgIds);
      newProcessingIds.delete(action.payload);
      const newPaymentProcessingIds = new Set(state.paymentProcessingOrgIds);
      newPaymentProcessingIds.delete(action.payload);

      return {
        ...state,
        processingOrgIds: newProcessingIds,
        paymentProcessingOrgIds: newPaymentProcessingIds,
        expandedOrgId: state.expandedOrgId === action.payload ? null : state.expandedOrgId,
        selectedOrgForCheckout:
          state.selectedOrgForCheckout === action.payload ? null : state.selectedOrgForCheckout,
        showPricingForOrg:
          state.showPricingForOrg === action.payload ? null : state.showPricingForOrg,
        confirmationState:
          state.confirmationState.orgId === action.payload
            ? { orgId: '', action: null }
            : state.confirmationState,
        selectedAction:
          state.selectedAction.orgId === action.payload
            ? { orgId: '', action: null }
            : state.selectedAction,
      };
    }

    case 'RESET_ALL':
      return { ...initialState, processingOrgIds: new Set(), paymentProcessingOrgIds: new Set() };

    default:
      return state;
  }
}

interface BillingContextType {
  // State
  expandedOrgId: string | null;
  selectedOrgForCheckout: string | null;
  showPricingForOrg: string | null;
  processingOrgIds: Set<string>;
  confirmationState: { orgId: string; action: 'cancel' | 'reactivate' | null };
  selectedAction: { orgId: string; action: 'update' | 'reactivate' | null };
  clientSecret: string | null;
  isFetchingClientSecret: boolean;
  validatedDiscountCode: string | null;
  validatedDiscountDescription: string | null;
  paymentProcessingOrgIds: Set<string>;

  // Computed values
  isOrgProcessing: (orgId: string) => boolean;
  isOrgExpanded: (orgId: string) => boolean;
  shouldShowCheckout: (orgId: string) => boolean;
  isPaymentProcessing: (orgId: string) => boolean;

  // Actions
  setExpandedOrg: (orgId: string | null) => void;
  setSelectedOrgForCheckout: (orgId: string | null) => void;
  setShowPricing: (orgId: string | null) => void;
  setProcessing: (orgId: string, isProcessing: boolean) => void;
  setConfirmationState: (orgId: string, action: 'cancel' | 'reactivate' | null) => void;
  setSelectedAction: (orgId: string, action: 'update' | 'reactivate' | null) => void;
  setClientSecret: (secret: string | null) => void;
  setFetchingClientSecret: (isFetching: boolean) => void;
  setDiscount: (code: string | null, description: string | null) => void;
  setPaymentProcessing: (orgId: string, isProcessing: boolean) => void;
  expandOrg: (orgId: string) => void;
  collapseOrg: (orgId: string) => void;
  resetOrgState: (orgId: string) => void;
  resetAll: () => void;
}

/**
 * Context for managing billing-related UI state across the billing components.
 */
const BillingContext = createContext<BillingContextType | undefined>(undefined);

/**
 * Provider component for the billing context.
 * Manages all billing UI state including expanded orgs, processing states, checkout flow, and discount validation.
 *
 * @param {object} props - The component props.
 * @param {ReactNode} props.children - The child components to render.
 * @returns {JSX.Element} The context provider wrapping children.
 */
export function BillingProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(billingReducer, initialState);

  // Action creators
  const setExpandedOrg = useCallback((orgId: string | null) => {
    dispatch({ type: 'SET_EXPANDED_ORG', payload: orgId });
  }, []);

  const setSelectedOrgForCheckout = useCallback((orgId: string | null) => {
    dispatch({ type: 'SET_SELECTED_ORG_FOR_CHECKOUT', payload: orgId });
  }, []);

  const setShowPricing = useCallback((orgId: string | null) => {
    dispatch({ type: 'SET_SHOW_PRICING', payload: orgId });
  }, []);

  const setProcessing = useCallback((orgId: string, isProcessing: boolean) => {
    dispatch({ type: 'SET_PROCESSING', payload: { orgId, isProcessing } });
  }, []);

  const setConfirmationState = useCallback(
    (orgId: string, action: 'cancel' | 'reactivate' | null) => {
      dispatch({ type: 'SET_CONFIRMATION_STATE', payload: { orgId, action } });
    },
    [],
  );

  const setSelectedAction = useCallback((orgId: string, action: 'update' | 'reactivate' | null) => {
    dispatch({ type: 'SET_SELECTED_ACTION', payload: { orgId, action } });
  }, []);

  const setClientSecret = useCallback((secret: string | null) => {
    dispatch({ type: 'SET_CLIENT_SECRET', payload: secret });
  }, []);

  const setFetchingClientSecret = useCallback((isFetching: boolean) => {
    dispatch({ type: 'SET_FETCHING_CLIENT_SECRET', payload: isFetching });
  }, []);

  const setDiscount = useCallback((code: string | null, description: string | null) => {
    dispatch({ type: 'SET_DISCOUNT', payload: { code, description } });
  }, []);

  const setPaymentProcessing = useCallback((orgId: string, isProcessing: boolean) => {
    dispatch({ type: 'SET_PAYMENT_PROCESSING', payload: { orgId, isProcessing } });
  }, []);

  const expandOrg = useCallback((orgId: string) => {
    dispatch({ type: 'SET_EXPANDED_ORG', payload: orgId });
  }, []);

  const collapseOrg = useCallback((orgId: string) => {
    dispatch({ type: 'RESET_ORG_STATE', payload: orgId });
  }, []);

  const resetOrgState = useCallback((orgId: string) => {
    dispatch({ type: 'RESET_ORG_STATE', payload: orgId });
  }, []);

  const resetAll = useCallback(() => {
    dispatch({ type: 'RESET_ALL' });
  }, []);

  // Computed values
  const isOrgProcessing = useCallback(
    (orgId: string) => state.processingOrgIds.has(orgId),
    [state.processingOrgIds],
  );
  const isOrgExpanded = useCallback(
    (orgId: string) => state.expandedOrgId === orgId,
    [state.expandedOrgId],
  );
  const shouldShowCheckout = useCallback(
    (orgId: string) => state.expandedOrgId === orgId && state.selectedOrgForCheckout === orgId,
    [state.expandedOrgId, state.selectedOrgForCheckout],
  );
  const isPaymentProcessing = useCallback(
    (orgId: string) => state.paymentProcessingOrgIds.has(orgId),
    [state.paymentProcessingOrgIds],
  );

  const contextValue: BillingContextType = {
    // State
    expandedOrgId: state.expandedOrgId,
    selectedOrgForCheckout: state.selectedOrgForCheckout,
    showPricingForOrg: state.showPricingForOrg,
    processingOrgIds: state.processingOrgIds,
    confirmationState: state.confirmationState,
    selectedAction: state.selectedAction,
    clientSecret: state.clientSecret,
    isFetchingClientSecret: state.isFetchingClientSecret,
    validatedDiscountCode: state.validatedDiscountCode,
    validatedDiscountDescription: state.validatedDiscountDescription,
    paymentProcessingOrgIds: state.paymentProcessingOrgIds,

    // Computed values
    isOrgProcessing,
    isOrgExpanded,
    shouldShowCheckout,
    isPaymentProcessing,

    // Actions
    setExpandedOrg,
    setSelectedOrgForCheckout,
    setShowPricing,
    setProcessing,
    setConfirmationState,
    setSelectedAction,
    setClientSecret,
    setFetchingClientSecret,
    setDiscount,
    setPaymentProcessing,
    expandOrg,
    collapseOrg,
    resetOrgState,
    resetAll,
  };

  return <BillingContext.Provider value={contextValue}>{children}</BillingContext.Provider>;
}

/**
 * Custom hook to access the billing context.
 * Provides an error if used outside of a BillingProvider.
 * @returns {BillingContextType} The billing context, including state and actions for managing billing UI.
 */
export function useBilling() {
  const context = useContext(BillingContext);
  if (context === undefined) {
    throw new Error('useBilling must be used within a BillingProvider');
  }
  return context;
}

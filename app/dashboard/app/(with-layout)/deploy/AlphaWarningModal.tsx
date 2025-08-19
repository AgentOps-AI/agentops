'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { AlertTriangle, Rocket } from 'lucide-react';

interface AlphaWarningModalProps {
  isOpen: boolean;
  onClose: () => void;
  onContinue: () => void;
}

export default function AlphaWarningModal({ isOpen, onClose, onContinue }: AlphaWarningModalProps) {
  const [hasJoinedAlpha, setHasJoinedAlpha] = useState(false);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-md mx-4 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center justify-center w-10 h-10 rounded-full bg-orange-100 dark:bg-orange-900/20">
              <AlertTriangle className="h-5 w-5 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h2 className="text-[16px] font-semibold text-gray-900 dark:text-white font-['Figtree']">
                Alpha Program
              </h2>
              <p className="text-[14px] text-gray-600 dark:text-gray-400 font-['Figtree']">
                Early access to deploy features
              </p>
            </div>
          </div>

          {/* Content */}
          <div className="space-y-4">
            <div className="flex items-start gap-3 p-4 bg-orange-50 dark:bg-orange-900/10 rounded-lg border border-orange-200 dark:border-orange-800">
              <Rocket className="h-5 w-5 text-orange-600 dark:text-orange-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[14px] text-gray-900 dark:text-white font-['Figtree'] font-medium mb-2">
                  Deploy is currently in Alpha
                </p>
                <p className="text-[14px] text-gray-600 dark:text-gray-400 font-['Figtree']">
                  This feature is still in development and may have limited functionality or stability issues. 
                  By joining the alpha program, you{"'"}ll get early access to new features and help us improve the product.
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <Checkbox
                  id="join-alpha"
                  checked={hasJoinedAlpha}
                  onCheckedChange={(checked) => setHasJoinedAlpha(checked as boolean)}
                  className="mt-1"
                />
                <label 
                  htmlFor="join-alpha" 
                  className="text-[14px] text-gray-900 dark:text-white font-['Figtree'] cursor-pointer"
                >
                  I understand this is an alpha feature and want to join the alpha program
                </label>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 mt-6">
            <Button
              variant="outline"
              onClick={onClose}
              className="flex-1 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Cancel
            </Button>
            <Button
              onClick={onContinue}
              disabled={!hasJoinedAlpha}
              className="flex-1 bg-orange-600 hover:bg-orange-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue to Deploy
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
} 
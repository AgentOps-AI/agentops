'use client';

import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useTraces } from '@/hooks/useTraces';

export function SurveyModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const { totalTraces } = useTraces();

  useEffect(() => {
    // Check if survey feature is enabled via environment variable
    const isSurveyEnabled = process.env.NEXT_PUBLIC_ENABLE_SURVEY === 'true';
    if (!isSurveyEnabled) return;

    const hasClosedSurvey = localStorage.getItem('has_closed_survey_request') === 'true';
    const lastDeclineTimestamp = localStorage.getItem('last_survey_decline_timestamp');
    const declineCount = parseInt(localStorage.getItem('survey_decline_count') || '0');
    
    const count = totalTraces ?? 0;
    const now = Date.now();
    const twoDaysInMs = 2 * 24 * 60 * 60 * 1000;
    
    let shouldShow = false;
    let newMessage = '';

    if (count > 5 && !hasClosedSurvey && declineCount === 0) {
      shouldShow = true;
      newMessage = "🎉 We noticed you've been using AgentOps! Want to help shape its future? Share your thoughts and we'll send you a swag bag - no strings attached!";
    } else if (count > 15 && declineCount === 1 && lastDeclineTimestamp) {
      const timeSinceLastDecline = now - parseInt(lastDeclineTimestamp);
      if (timeSinceLastDecline >= twoDaysInMs) {
        shouldShow = true;
        newMessage = "🚀 You've been using AgentOps even more! Huge! We'd love to hear your thoughts on how we can make it even better for you. PLUS we'll give you AgentOps goodies :)";
      }
    } else if (count > 50 && declineCount === 2 && lastDeclineTimestamp) {
      const timeSinceLastDecline = now - parseInt(lastDeclineTimestamp);
      if (timeSinceLastDecline >= twoDaysInMs) {
        shouldShow = true;
        newMessage = "🌟 Aight, now you're officially an AgentOps power user! Your feedback could help thousands of others. Let's chat for 5 minutes and we'll upgrade you to Pro for 2 months - our treat!";
      }
    }

    if (shouldShow) {
      setMessage(newMessage);
      setIsOpen(true);
    }
  }, [totalTraces]);

  const handleClose = () => {
    const currentCount = parseInt(localStorage.getItem('survey_decline_count') || '0');
    localStorage.setItem('survey_decline_count', (currentCount + 1).toString());
    localStorage.setItem('last_survey_decline_timestamp', Date.now().toString());
    
    if (currentCount + 1 >= 3) {
      localStorage.setItem('has_closed_survey_request', 'true');
    }
    
    setIsOpen(false);
  };

  const handleTakeSurvey = () => {
    // Replace with your actual survey URL
    window.open('https://cal.com/team/agency-ai/agentops-feedback', '_blank');
    localStorage.setItem('has_closed_survey_request', 'true');
    setIsOpen(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold text-center">
            🎁 AgentOps Swag Bag 🖇️
          </DialogTitle>
          <DialogDescription className="text-center mt-2">
            {message}
          </DialogDescription>
        </DialogHeader>
        <div className="mt-4 p-4 bg-blue-50 rounded-lg">
          <h3 className="font-semibold text-blue-800">What&apos;s in the goodie bag:</h3>
          <ul className="mt-2 space-y-2 text-sm text-blue-700">
            <li>✓ AgentOps stickers</li>
            <li>✓ Midjourney magazine</li>
            <li>✓ Our undying love and support 🫶</li>
          </ul>
        </div>
        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={handleClose}>
            Not right now
          </Button>
          <Button onClick={handleTakeSurvey} className="bg-blue-600 hover:bg-blue-700">
            Get Goodies & Share Feedback
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 
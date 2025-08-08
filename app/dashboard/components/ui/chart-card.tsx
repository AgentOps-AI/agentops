import { memo, ReactNode } from 'react';
import { Container } from './container';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './card';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './tooltip';
import { HelpCircleIcon } from 'hugeicons-react';

function ChartCardCmp({
  title,
  subTitle,
  description,
  children,
  footerContent,
  cardStyles,
  footerStyles,
  tooltipContent,
  cardTitleStyles,
  cardTitleTextStyles,
  cardHeaderStyles,
  cardContentStyles,
  containerStyles,
}: {
  title?: string;
  subTitle?: string;
  description?: string;
  children: ReactNode;
  footerContent?: ReactNode;
  cardStyles?: string;
  footerStyles?: string;
  tooltipContent?: ReactNode;
  cardTitleStyles?: string;
  cardTitleTextStyles?: string;
  cardHeaderStyles?: string;
  cardContentStyles?: string;
  containerStyles?: string;
}) {
  return (
    <Container className={cn('rounded-2xl bg-[#F7F8FF] dark:bg-transparent', containerStyles)}>
      <Card
        className={cn(
          'rounded-xl border-white bg-transparent px-3 shadow-xl transition-all duration-300',
          cardStyles,
        )}
      >
        <CardHeader className={cn('mb-4 mt-3', cardHeaderStyles)}>
          <CardTitle
            className={cn(
              'flex flex-col text-xl font-medium text-primary',
              cardTitleStyles,
            )}
          >
            <div className={cn('flex flex-col', cardTitleTextStyles)}>
              {title && (
                <div className="flex items-center gap-2">
                  <span>{title}</span>
                  {tooltipContent && (
                    <TooltipProvider delayDuration={200}>
                      <Tooltip>
                        <TooltipTrigger>
                          <HelpCircleIcon className="h-3.5 w-3.5 cursor-pointer" />
                        </TooltipTrigger>
                        <TooltipContent
                          className="w-1/5 rounded-xl bg-primary/80 p-3 font-light text-[#EBECF8] backdrop-blur-md sm:ml-64 sm:w-72"
                          side="bottom"
                          sideOffset={8}
                        >
                          {tooltipContent}
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}
                </div>
              )}
              {subTitle && <div className="text-base text-secondary dark:text-white">{subTitle}</div>}
            </div>
          </CardTitle>
          {description && (
            <CardDescription className="font-medium text-secondary">{description}</CardDescription>
          )}
        </CardHeader>
        <CardContent className={cardContentStyles}>{children}</CardContent>
        {footerContent && <CardFooter className={footerStyles}>{footerContent}</CardFooter>}
      </Card>
    </Container>
  );
}

export const ChartCard = memo(ChartCardCmp);

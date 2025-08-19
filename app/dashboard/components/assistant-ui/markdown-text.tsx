"use client";

import "@assistant-ui/react-markdown/styles/dot.css";

import {
  CodeHeaderProps,
  MarkdownTextPrimitive,
  unstable_memoizeMarkdownComponents as memoizeMarkdownComponents,
  useIsMarkdownCodeBlock,
} from "@assistant-ui/react-markdown";
import remarkGfm from "remark-gfm";
import { FC, memo, useState, useEffect } from "react";
import { CheckIcon } from "lucide-react";
import { Copy01Icon as CopyIcon } from "hugeicons-react";

import { TooltipIconButton } from "@/components/assistant-ui/tooltip-icon-button";
import { cn } from "@/lib/utils";

const MarkdownTextImpl = () => {
  useEffect(() => {
    const style = document.createElement('style');
    style.innerHTML = `
      .aui-md .aui-code-header {
        background-color: #292F47 !important;
        border-top-left-radius: 0.5rem !important;
        border-top-right-radius: 0.5rem !important;
        padding: 0.35rem 0.75rem !important;
        min-height: unset !important;
        height: auto !important;
      }
      .aui-md pre {
        background-color: #1e2130 !important;
        font-family: Menlo, monospace !important;
      }
      .aui-md code {
        font-family: Menlo, monospace !important;
      }
      .aui-code-header .tooltip-icon-button {
        padding: 0.25rem !important;
        height: 1.5rem !important;
        width: 1.5rem !important;
      }
      .aui-code-header .tooltip-icon-button svg {
        height: 0.85rem !important;
        width: 0.85rem !important;
      }
    `;
    document.head.appendChild(style);
    return () => {
      document.head.removeChild(style);
    };
  }, []);

  return (
    <MarkdownTextPrimitive
      remarkPlugins={[remarkGfm]}
      className="aui-md"
      components={defaultComponents}
    />
  );
};

export const MarkdownText = memo(MarkdownTextImpl);

const CodeHeader: FC<CodeHeaderProps> = ({ language, code }) => {
  const { isCopied, copyToClipboard } = useCopyToClipboard();
  const onCopy = () => {
    if (!code || isCopied) return;
    copyToClipboard(code);
  };

  // Display "markdown" if language is "unknown" or empty
  const displayLanguage = !language || language === "unknown" ? "markdown" : language;

  return (
    <div
      className="aui-code-header flex items-center justify-between gap-2 rounded-t-lg bg-[#292F47] !bg-[#292F47] px-3 py-1.5 text-xs font-semibold text-white"
      style={{ backgroundColor: "#292F47", borderTopLeftRadius: "0.5rem", borderTopRightRadius: "0.5rem" }}
    >
      <span className="lowercase [&>span]:text-xs">{displayLanguage}</span>
      <TooltipIconButton tooltip="Copy" onClick={onCopy} className="tooltip-icon-button h-6 w-6 p-1">
        {!isCopied && <CopyIcon className="h-3.5 w-3.5 text-[rgba(225,226,242,1)]" />}
        {isCopied && <CheckIcon className="h-3.5 w-3.5 text-[rgba(75,196,152,1)]" />}
      </TooltipIconButton>
    </div>
  );
};

const useCopyToClipboard = ({
  copiedDuration = 3000,
}: {
  copiedDuration?: number;
} = {}) => {
  const [isCopied, setIsCopied] = useState<boolean>(false);

  const copyToClipboard = (value: string) => {
    if (!value) return;

    navigator.clipboard.writeText(value).then(() => {
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), copiedDuration);
    });
  };

  return { isCopied, copyToClipboard };
};

const defaultComponents = memoizeMarkdownComponents({
  h1: ({ className, ...props }) => (
    <h1 className={cn("mb-8 scroll-m-20 text-4xl font-extrabold tracking-tight last:mb-0", className)} {...props} />
  ),
  h2: ({ className, ...props }) => (
    <h2 className={cn("mb-4 mt-8 scroll-m-20 text-3xl font-semibold tracking-tight first:mt-0 last:mb-0", className)} {...props} />
  ),
  h3: ({ className, ...props }) => (
    <h3 className={cn("mb-4 mt-6 scroll-m-20 text-2xl font-semibold tracking-tight first:mt-0 last:mb-0", className)} {...props} />
  ),
  h4: ({ className, ...props }) => (
    <h4 className={cn("mb-4 mt-6 scroll-m-20 text-xl font-semibold tracking-tight first:mt-0 last:mb-0", className)} {...props} />
  ),
  h5: ({ className, ...props }) => (
    <h5 className={cn("my-4 text-lg font-semibold first:mt-0 last:mb-0", className)} {...props} />
  ),
  h6: ({ className, ...props }) => (
    <h6 className={cn("my-4 font-semibold first:mt-0 last:mb-0", className)} {...props} />
  ),
  p: ({ className, ...props }) => (
    <p className={cn("mb-5 mt-5 leading-7 first:mt-0 last:mb-0", className)} {...props} />
  ),
  a: ({ className, ...props }) => (
    <a className={cn("text-slate-900 font-medium underline underline-offset-4 dark:text-slate-50", className)} {...props} />
  ),
  blockquote: ({ className, ...props }) => (
    <blockquote className={cn("border-l-2 pl-6 italic", className)} {...props} />
  ),
  ul: ({ className, ...props }) => (
    <ul className={cn("my-5 ml-6 list-disc [&>li]:mt-2", className)} {...props} />
  ),
  ol: ({ className, ...props }) => (
    <ol className={cn("my-5 ml-6 list-decimal [&>li]:mt-2", className)} {...props} />
  ),
  hr: ({ className, ...props }) => (
    <hr className={cn("my-5 border-b", className)} {...props} />
  ),
  table: ({ className, ...props }) => (
    <table className={cn("my-5 w-full border-separate border-spacing-0 overflow-y-auto", className)} {...props} />
  ),
  th: ({ className, ...props }) => (
    <th className={cn("bg-slate-100 px-4 py-2 text-left font-bold first:rounded-tl-lg last:rounded-tr-lg [&[align=center]]:text-center [&[align=right]]:text-right dark:bg-slate-800", className)} {...props} />
  ),
  td: ({ className, ...props }) => (
    <td className={cn("border-b border-l px-4 py-2 text-left last:border-r [&[align=center]]:text-center [&[align=right]]:text-right", className)} {...props} />
  ),
  tr: ({ className, ...props }) => (
    <tr className={cn("m-0 border-b p-0 first:border-t [&:last-child>td:first-child]:rounded-bl-lg [&:last-child>td:last-child]:rounded-br-lg", className)} {...props} />
  ),
  sup: ({ className, ...props }) => (
    <sup className={cn("[&>a]:text-xs [&>a]:no-underline", className)} {...props} />
  ),
  pre: ({ className, ...props }) => (
    <pre
      className={cn("overflow-x-auto rounded-b-lg !bg-[#1e2130] bg-[#1e2130] p-4 text-white font-['Menlo']", className)}
      style={{ backgroundColor: "#1e2130" }}
      {...props}
    />
  ),
  code: function Code({ className, ...props }) {
    const isCodeBlock = useIsMarkdownCodeBlock();
    return (
      <code
        className={cn(
          !isCodeBlock && "rounded border border-[rgba(222,224,244,1)] !bg-[#f8f9fc] bg-[#f8f9fc] px-1 py-0.5 font-['Menlo'] text-[rgba(20,27,52,1)] dark:!bg-[#1e2130] dark:bg-[#1e2130] dark:text-[rgba(225,226,242,1)]",
          isCodeBlock && "font-['Menlo'] !bg-[#1e2130] bg-[#1e2130]",
          className
        )}
        style={isCodeBlock ? { backgroundColor: "#1e2130" } : null}
        {...props}
      />
    );
  },
  CodeHeader,
});

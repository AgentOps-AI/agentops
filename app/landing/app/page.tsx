import * as React from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import ToolkitText from '@/components/text/toolkit-text';
import IntegratesText from '@/components/text/integrates-with';
import ObserveText from '@/components/text/observe';
import AgentsProductionText from '@/components/text/agents-production';
import TrustedPartnersText from '@/components/text/trusted-partners';
import Link from 'next/link';
import {
  Github,
  LineChart,
  LockKeyhole,
  MoveRight,
  Rocket,
  UserSearch,
  History,
  BookText,
  ArrowUp10,
  CircleDollarSign,
  BookOpen,
} from 'lucide-react';

type NavbarItem = {
  text: string;
  href: string;
};

type NavbarProps = {
  items: NavbarItem[];
};

type ImageProps = {
  src: string;
  alt?: string;
  className?: string;
};

const Image: React.FC<ImageProps> = ({ src, alt, className }) => (
  <img src={src} alt={alt || ''} className={className} loading="lazy" />
);

const customStyle = {
  'pre[class*="language-"]': {
    color: '#9718FB',
    // background: '#0F1117',
  },
  keyword: {
    color: '#FF6535',
  },
  'class-name': {
    color: '#4ec9b0',
  },
  'maybe-class-name': {
    color: '#4ec9b0',
  },
  comment: {
    color: '#141B34',
  },
  function: {
    color: '#9718FB',
  },
  string: {
    color: '#2400FF',
  },
  builtin: {
    color: '#ce9178',
  },
};

export default function Home() {
  return (
    <div className="flex flex-col">
      <Navbar
        items={[
          { text: 'Pricing', href: '/pricing' },
          { text: 'Docs', href: 'https://docs.agentops.ai' },
        ]}
      />
      <Banner />
      <HeroImage />
      <Integrations />
      <Observations />
      <Productionize />
      <TrustedPartners />
      <GetStarted />
    </div>
  );
}

function Navbar({ items }: NavbarProps) {
  return (
    <header className="flex w-full justify-between gap-5">
      <div className="my-auto flex gap-2.5 whitespace-nowrap px-5 text-lg font-semibold leading-7 tracking-tighter text-zinc-900">
        <Image
          src="/logo.svg"
          className="aspect-[1.12] w-[35px] shrink-0 fill-zinc-900"
          alt="AgentOps Logo"
        />
        <div>AgentOps.ai</div>
      </div>
      <nav className="flex items-center justify-between gap-5 text-sm max-md:flex-wrap ">
        {items.map((item, index) => (
          <Link
            key={index}
            href={item.href}
            className="text-right font-semibold leading-6 text-slate-900 text-opacity-70"
          >
            {item.text}
          </Link>
        ))}
        <div className="flex">
          <div className="my-auto h-[33px] w-px shrink-0 bg-slate-900 bg-opacity-20" />
          <div className="flex gap-4 px-5">
            <Link
              href="https://app.agentops.ai/signin"
              className="hover:bg-primary-button-hover bg-primary-button shadow-primary-button flex items-center rounded-md bg-cover px-5 font-medium text-white"
            >
              <LockKeyhole className="mr-1 w-4" /> Sign Up
            </Link>
          </div>
        </div>
      </nav>
    </header>
  );
}

function Banner() {
  return (
    <main className="mt-36 flex w-full flex-col justify-center md:px-16">
      <section className="flex w-full max-w-[1054px] flex-col self-center">
        <header className="flex flex-col text-center">
          <div className="max-h-36">
            <ToolkitText />
          </div>
          <p className="mt-16 self-center text-lg text-zinc-900 text-opacity-80">
            Are you ready to build enterprise-ready AI agents
          </p>
        </header>
        <section className="mt-9 flex w-[279px] max-w-full flex-col justify-center self-center text-sm font-medium leading-6 text-white">
          <div className="flex justify-center gap-5">
            <Link
              href="https://app.agentops.ai"
              className=" hover:bg-purple-button-hover bg-purple-button shadow-purple-button flex items-center rounded-md bg-cover px-5 font-medium text-white"
            >
              Get Started <MoveRight className="my-2 ml-1 w-4" />
            </Link>
            <Link
              href="https://github.com/AgentOps-AI/agentops"
              className="hover:bg-primary-button-hover bg-primary-button shadow-primary-button flex items-center rounded-md bg-cover px-5 font-medium text-white"
            >
              <BookOpen className="my-2 mr-1 w-4" /> Docs
            </Link>
          </div>
        </section>
      </section>
    </main>
  );
}

function HeroImage() {
  return (
    <>
      <section className="flex w-full flex-col items-center justify-center pt-16">
        <div className="grid max-w-[1150px] grid-cols-1 gap-5 lg:grid-cols-3">
          <div className="bg-card-background bg-50% rounded-xl bg-[url('/static-only.png')] bg-repeat p-4 shadow-2xl md:p-10 lg:col-span-2">
            <img src="/waterfall.png" alt="Waterfall" />
          </div>
          <div className="bg-card-background bg-50% col-span-1 grow break-words rounded-xl bg-[url('/static-only.png')] bg-repeat shadow-2xl">
            <div className="font-jetbrains p-8">pip install agentops</div>
            <hr />
            <SyntaxHighlighter
              language={'python'}
              style={customStyle}
              className="font-jetbrains p-8"
            >
              {`import agentops
#Beginning of program's code (i.e. main.py, __init__.py)
agentops.init(<API KEY>)

...
# (optional: record specific functions) 
@agentops.record_function('sample function being record')
def sample_function(...):
...

# End of program
agentops.end_session('Success')
# Woohoo You're done 🎉`}
            </SyntaxHighlighter>
          </div>

          <div className="bg-card-background bg-50% grow rounded-xl bg-[url('/static-only.png')] bg-repeat p-10 shadow-2xl lg:col-span-3">
            <div className="grid max-w-[1080px] gap-16 md:grid-cols-3">
              <div>
                <div className="flex items-center">
                  <LineChart color="#6E43DC" />
                  <h3 className="ml-1 text-lg font-semibold">Visual insights</h3>
                </div>
                <p className="pt-1 text-sm">
                  We provide developers with waterfall graphs to see what their agents are doing,
                  making it better than just using a terminal
                </p>
              </div>

              <div>
                <div className="flex items-center">
                  <History color="#6E43DC" />
                  <h3 className="ml-1 text-lg font-semibold">Time travel debugging</h3>
                </div>
                <p className="pt-1 text-sm">
                  Developers can go back and edit previous prompts to make their agents more
                  reliable
                </p>
              </div>

              <div>
                <div className="flex items-center">
                  <BookText color="#6E43DC" />
                  <h3 className="ml-1 flex text-lg font-semibold">Comprehensive output</h3>
                </div>
                <p className="pt-1 text-sm">
                  Developers can access all outputs from their LLM calls.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

function Integrations() {
  return (
    <section className="flex w-full items-center justify-center px-16 pt-20 text-center">
      <div className="flex w-full max-w-[1080px] flex-col">
        <div className="flex flex-col justify-center">
          <h2 className="self-center">
            <IntegratesText />
          </h2>
          <div className="mt-6 self-center text-lg text-zinc-900 text-opacity-80">
            We help developers move prototypes into real-world production.
          </div>
        </div>
        <img src="/integrations.png" className="mt-11 w-[1000px] self-center" />
      </div>
    </section>
  );
}

function Observations() {
  return (
    <section className="flex w-full max-w-[1080px] flex-col self-center pt-36">
      <div className="flex w-full max-w-[938px] flex-col justify-center self-center text-center ">
        <div className="flex flex-col px-5">
          <h2 className="text-6xl text-zinc-900">
            <ObserveText />
          </h2>
          <div className="mt-6 self-center text-lg text-zinc-900 text-opacity-80">
            Informative information at a glance
          </div>
        </div>
      </div>
      <div className="bg-card-background bg-50% mt-10 max-w-[1080px] grow rounded-xl bg-[url('/static-only.png')] bg-repeat p-10 pb-0 shadow-2xl">
        <img src="/graphs.png" alt="features" />
      </div>
      <div className="bg-card-background bg-50% mt-5 max-w-[1080px] grow rounded-xl bg-[url('/static-only.png')] bg-repeat p-10 shadow-2xl">
        <div className="flex justify-center">
          <div className="grid max-w-lg gap-10 sm:grid-cols-2">
            <div>
              <div className="flex items-center">
                <ArrowUp10 color="#6E43DC" />
                <h3 className="ml-1 text-lg font-semibold">Token Counts</h3>
              </div>
              <p className="pt-1 text-sm">Developers can monitor token usage for efficiency</p>
            </div>
            <div>
              <div className="flex items-center">
                <CircleDollarSign color="#6E43DC" />
                <h3 className="ml-1 flex text-lg font-semibold">Cost tracking</h3>
              </div>
              <p className="pt-1 text-sm">
                Developers can track costs associated with their agents
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Productionize() {
  return (
    <section className="mt-40 flex w-full max-w-[1080px] flex-col self-center">
      <div className="flex flex-col self-center text-center">
        <h2 className="w-full max-w-[1080px]">
          <AgentsProductionText />
        </h2>
        <div className="mt-6 self-center text-lg text-zinc-900 text-opacity-80">
          Streamline deployment for maximum efficiency
        </div>
      </div>
      <div className="mt-11 justify-center">
        <div className="grid gap-10 md:grid-cols-2">
          <div className="ml-5 flex grow flex-col">
            <Link href="https://agen.cy">
              <div className="bg-card-background bg-50% flex min-h-[249px] grow flex-col justify-between rounded-xl bg-[url('/static-only.png')] bg-repeat px-9 pb-4 pt-6 shadow-2xl hover:shadow-inner">
                <UserSearch color="#6E43DC" />
                <div className="relative flex w-[252px] max-w-full flex-col">
                  <div className="text-lg font-medium leading-7 text-zinc-900">Hire an Agent</div>
                  <div className="mt-2 text-base leading-5 text-zinc-900 text-opacity-80">
                    Either by an approved off the shelf or consult with one of our expert agent
                    developers.
                  </div>
                </div>
                <MoveRight color="#6E43DC" className="self-end" />
              </div>
            </Link>
          </div>
          <div className="ml-5 flex flex-col">
            <Link href="https://calendly.com/itsada">
              <div className="bg-card-background bg-50% flex min-h-[249px] grow flex-col justify-between rounded-xl bg-[url('http://localhost:3000/static-only.png')] bg-repeat px-9 pb-4 pt-6 shadow-2xl hover:shadow-inner">
                <Rocket color="#6E43DC" />
                <div className="relative flex w-[252px] max-w-full flex-col">
                  <div className="text-lg font-medium leading-7 text-zinc-900">
                    Scale to Enterprise
                  </div>
                  <div className="mt-2 text-base leading-5 text-zinc-900 text-opacity-80">
                    Bridge your prototype to production with enterprise grade monitoring and
                    compliance.
                  </div>
                </div>
                <MoveRight color="#6E43DC" className="self-end" />
              </div>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

function TrustedPartners() {
  return (
    <section className="flex w-full max-w-[1080px] flex-col self-center pt-36">
      <div className="flex items-center justify-center px-16 text-center">
        <div className="flex flex-col">
          <h2 className="h-14">
            <TrustedPartnersText />
          </h2>
          <p className="mt-6 self-center text-lg text-zinc-900 text-opacity-80">
            {' '}
            Proudly collaborate with{' '}
          </p>
        </div>
      </div>

      <div className="mt-11 grid items-center justify-center justify-items-center gap-5 px-7 lg:flex">
        <img src="/crewai.png" className="my-auto w-[110px]" alt="CrewAI" />
        <img src="/langchain.png" className="my-auto w-[180px]" alt="LangChain" />
        <img src="/cohere.svg" className="my-auto w-[180px]" alt="Cohere" />
        <img src="/autogen.png" className="my-auto w-[125px]" alt="AutoGen" />
        <img src="/superagent.png" className="my-auto w-[180px]" alt="Superagent" />
        <img src="/promptarmor.svg" className="my-auto w-[60px]" alt="PromptArmor" />
        <img src="/openpipe.png" className="my-auto w-[110px]" alt="OpenPipe" />
      </div>
    </section>
  );
}

function GetStarted() {
  return (
    <section className="flex w-full max-w-[1080px] flex-col self-center">
      <img src="/ready.png" className="mt-24 aspect-[2.3] w-full" alt="Graph overview" />
      <div className="relative left-[100px] top-[-250px]">
        <div className="hidden gap-5 lg:flex">
          <Link
            href="https://app.agentops.ai"
            className="hover:bg-purple-button-hover bg-purple-button shadow-purple-button flex items-center rounded-md bg-cover px-5 font-medium text-white"
          >
            Get Started <MoveRight className="my-2 ml-1 w-4" />
          </Link>
          <Link
            href="https://github.com/AgentOps-AI/agentops"
            className="hover:bg-primary-button-hover bg-primary-button shadow-primary-button flex items-center rounded-md bg-cover px-5 font-medium text-white"
          >
            <BookOpen className="my-2 mr-1 w-4" /> Docs
          </Link>
        </div>
      </div>
    </section>
  );
}

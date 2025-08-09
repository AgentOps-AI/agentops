import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="mt-36 flex w-full flex-col self-center">
      <div className="mt-24 flex flex-col">
        <div className="w-[460px] max-w-full">
          <section className="flex gap-5 max-md:flex-col max-md:gap-0">
            <article className="flex w-2/5 flex-col max-md:ml-0 max-md:w-full">
              <header className="flex gap-2.5 whitespace-nowrap px-5 text-lg font-semibold leading-7 tracking-tighter text-zinc-900">
                <img
                  src="/logo.svg"
                  className="aspect-[1.1] w-[35px] shrink-0 fill-zinc-900"
                  alt="AgentOps.ai Logo"
                />
                <div>AgentOps.ai</div>
              </header>
            </article>
            <article className="ml-5 flex w-3/5 flex-col">
              <nav className="flex grow justify-between gap-5 pr-7 text-sm leading-6">
                <div className="flex flex-col">
                  <p className="font-semibold text-black">General</p>
                  <p className="mt-1.5 text-zinc-900 text-opacity-80">
                    {' '}
                    <Link href="https://docs.agentops.ai">Documentation</Link> <br />{' '}
                    <Link href="/contact-us">Enterprise</Link> <br />{' '}
                    <Link href="https://agents.staf.ai/Staf">View all Agents</Link>{' '}
                  </p>
                </div>
                <div className="flex flex-col self-start">
                  <p className="font-semibold text-black">Company</p>
                  <p className="mt-1.5 text-zinc-900 text-opacity-80">
                    {' '}
                    <Link href="/contact-us">Contact us</Link> <br />{' '}
                    <Link href="https://app.agentops.ai">Dashboard</Link>{' '}
                  </p>
                </div>
              </nav>
            </article>
          </section>
        </div>
        <div className="mt-12 flex w-full justify-between gap-5">
          <p className="text-sm leading-6 tracking-normal text-slate-900">
            {' '}
            2024 © All rights reserved{' '}
          </p>
          <div className="my-auto flex gap-3.5">
            <Link href="https://discord.gg/FagdcwwXRR">
              <img src="/discord.svg" className="aspect-square w-5 shrink-0" alt="Discord" />
            </Link>
            <Link href="https://github.com/AgentOps-AI/agentops">
              <img src="/github.svg" className="aspect-square w-5 shrink-0" alt="Github" />
            </Link>
            <Link href="https://twitter.com/AgentOpsAI">
              <img src="/new-twitter.svg" className="aspect-square w-5 shrink-0" alt="Twitter" />
            </Link>
            <Link href="https://www.linkedin.com/company/aistaff/">
              <img src="/linkedin-01.svg" className="aspect-square w-5 shrink-0" alt="LinkedIn" />
            </Link>
            <Link href="https://calendly.com/itsada">
              <img src="/calendar-03.svg" className="aspect-square w-5 shrink-0" alt="Calendar" />
            </Link>
            <Link href="mailto:adam@agentops.ai">
              <img src="mail-02.svg" className="aspect-square w-5 shrink-0" alt="Email" />
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}

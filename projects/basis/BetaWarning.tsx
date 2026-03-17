// components/BetaWarning.tsx
"use client";

import Link from "next/link";
import Image from "next/image";
import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { useUser } from "@/contexts/UserContext";

const WARNING_ACCEPTED_KEY = "beta_warning_accepted_v4";

// Pages that should never show the beta gate (marketing / public pages)
const EXCLUDED_PATHS = ["/", "/index", "/blog", "/api-docs"];

export default function BetaWarning({ children }: { children: React.ReactNode }) {
  const [showWarning, setShowWarning] = useState(false);
  const { isDarkMode } = useUser();
  const pathname = usePathname();

  useEffect(() => {
    const accepted = localStorage.getItem(WARNING_ACCEPTED_KEY);
    const isExcluded = EXCLUDED_PATHS.includes(pathname) || pathname.startsWith("/blog/");

    if (!isExcluded && !accepted) {
      setShowWarning(true);
    }
  }, [pathname]);

  const handleAccept = () => {
    localStorage.setItem(WARNING_ACCEPTED_KEY, "true");
    setShowWarning(false);
  };

  useEffect(() => {
    if (showWarning) {
      document.body.classList.add("overflow-hidden");
    } else {
      document.body.classList.remove("overflow-hidden");
    }
    return () => document.body.classList.remove("overflow-hidden");
  }, [showWarning]);

  if (!showWarning) {
    return <>{children}</>;
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center overflow-auto pb-2">
        <div
          className={`relative sm:max-w-lg w-full sm:h-fit h-full sm:rounded-2xl p-6 sm:p-8 sm:shadow-2xl sm:border ${
            isDarkMode
              ? "bg-gray-900 sm:border-gray-700 text-white"
              : "bg-white sm:border-gray-300 text-gray-900"
          }`}
        >
          {/* Logo */}
          <div className="flex justify-center mb-6">
            <Image src={isDarkMode ? "/basis-logo.svg" : "/basis-logo-dark.svg"} alt="BASIS" width={120} height={40} />
          </div>

          <h2 className="text-xl sm:text-2xl font-bold text-center mb-2 leading-tight">
            YOU&apos;RE EARLY
          </h2>
          <p className={`text-center text-sm mb-8 ${isDarkMode ? "text-gray-400" : "text-gray-500"}`}>
            Public Beta — Live on BNB Chain
          </p>

          <div className="space-y-4 text-sm sm:text-base leading-relaxed">
            <p>
              <strong>Every action earns airdrop points.</strong> Trade, create tokens, bet on predictions, lend, and stake — all with free test USD from the faucet. Only BNB gas is real.
            </p>

            <div className={`rounded-xl p-4 ${isDarkMode ? "bg-white/5 border border-white/10" : "bg-gray-50 border border-gray-200"}`}>
              <p className={`text-xs sm:text-sm ${isDarkMode ? "text-gray-300" : "text-gray-600"}`}>
                Smart contracts are undergoing a full security audit by:
              </p>
              <Link href="https://hashlock.com" target="_blank" className={`mt-2 flex flex-row gap-2 items-center w-fit ${isDarkMode ? "hover:opacity-80" : "hover:opacity-70"} transition-opacity`}>
                <Image src="/hashlock.png" width={24} height={24} alt="hashlock" />
                <span className="font-bold italic text-lg">hashlock<span className="text-[#00e4b5] text-2xl">.</span></span>
              </Link>
            </div>

            <ul className={`space-y-2.5 text-xs sm:text-sm ${isDarkMode ? "text-gray-300" : "text-gray-600"}`}>
              <li className="flex items-start gap-2">
                <span className="text-green-400 mt-0.5">&#10003;</span>
                Points earned now count toward the BASIS airdrop
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-0.5">&#10003;</span>
                First 500 wallets get Early Bird bonus (+50% on all points)
              </li>
              <li className="flex items-start gap-2">
                <span className="text-purple-400 mt-0.5">&#10003;</span>
                Claim free test USD from the faucet — zero risk, real rewards
              </li>
            </ul>

            <p className={`text-xs sm:text-sm mt-6 ${isDarkMode ? "text-gray-500" : "text-gray-400"}`}>
              Features and contracts may change during beta. Report bugs to earn bonus points.
            </p>
          </div>

          <div className="mt-8 flex justify-center">
            <button
              onClick={handleAccept}
              className="px-10 py-3 sm:py-4 rounded-xl font-semibold text-base sm:text-lg transition-all active:scale-95 bg-blue-600 hover:bg-blue-700 text-white"
            >
              Start Earning
            </button>
          </div>
        </div>
      </div>

      {/* Blurred background */}
      <div className="blur-sm pointer-events-none">{children}</div>
    </>
  );
}

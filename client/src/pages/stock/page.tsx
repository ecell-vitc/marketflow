import { useState, useEffect, useRef } from "react";
import type { Stock as StockType, StockEntry } from "../../types";
import { parse_entry } from "./logic";
import { makeRequest, SERVER_HOST, SERVER_WS_PROTOCOL } from "../../lib/utils";
import Stock from "./stock";

const Page = () => {
  const [stocks, setStocks] = useState<Record<string, StockType> | null>(null);
  const [entries, setEntries] = useState<Record<string, StockEntry[]> | null>(null);
  const [curr, setCurr] = useState<string>("");

  const mounted = useRef(true);

  useEffect(() => {
    makeRequest("stocks", "GET")
      .then(parse_entry)
      .then((data) => {
        setStocks(data.info);
        setEntries(data.data);
        setCurr(Object.keys(data.info)[0]);
      });

    const socket = new WebSocket(`${SERVER_WS_PROTOCOL}://${SERVER_HOST}/stocks/`);

    socket.onmessage = (ev) => {
      const update: Record<string, StockEntry> = JSON.parse(ev.data);

      setEntries((prev) => {
        if (!prev) return prev;
        const res = structuredClone(prev);

        Object.keys(update).forEach((id) => {
          if (!res[id]) return;
          const last = res[id].length - 1;
          if (res[id][last].time === update[id].time)
            res[id][last] = update[id];
          else res[id].push(update[id]);
        });

        return res;
      });
    };

    return () => {
      mounted.current = false;
      socket.close();
    };
  }, []);

  if (!stocks || !entries) return null;

  return (
    <div className="min-h-screen text-white">
      <Stock
        stocks={stocks}
        entries={entries}
        curr={curr}
        setCurr={setCurr}
      />
    </div>
  );
};

export default Page;

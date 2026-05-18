//+------------------------------------------------------------------+
//|  SonicCopyX Receiver — MT4 Slave EA                             |
//|  Cita signale iz dijeljenog fajla i kopira trejdove              |
//+------------------------------------------------------------------+
#property copyright "Sonic AI CopyX"
#property version   "1.00"
#property strict

input string SignalFile      = "SonicCopyX_signal.csv"; // Isti fajl kao u Senderu
input int    TimerSec        = 1;                        // Interval citanja (sekunde)
input int    Slippage        = 30;                       // Max slippage (points)
input int    MagicNumber     = 88888;                    // Magic za slave pozicije
input int    HeartbeatTimeout = 10;                      // Sekundi bez heartbeata = sender offline
input bool   CloseIfSenderOffline = true;                // Zatvori pozicije ako sender offline

// Interna stanja
datetime gLastHeartbeat = 0;
bool     gSenderOnline  = false;

struct MasterPos {
   long   ticket;
   string symbol;
   int    type;      // 0=BUY, 1=SELL
   double lots;
   double openPrice;
   double sl;
   double tp;
   long   magic;
   long   openTime;
};

MasterPos gMasterPositions[];
int       gMasterCount = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   EventSetTimer(TimerSec);
   Print("SonicCopyX Receiver pokrenut.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

//+------------------------------------------------------------------+
void OnTimer()
{
   if (!ReadSignalFile())
   {
      HandleSenderOffline();
      return;
   }

   // Provjeri heartbeat
   if ((int)TimeCurrent() - (int)gLastHeartbeat > HeartbeatTimeout)
   {
      HandleSenderOffline();
      return;
   }

   gSenderOnline = true;
   SyncPositions();
}

//+------------------------------------------------------------------+
bool ReadSignalFile()
{
   int handle = FileOpen(SignalFile, FILE_READ | FILE_TXT | FILE_COMMON | FILE_ANSI);
   if (handle == INVALID_HANDLE)
      return false;

   gMasterCount = 0;
   ArrayResize(gMasterPositions, 0);

   while (!FileIsEnding(handle))
   {
      string line = FileReadString(handle);
      line = StringTrimRight(StringTrimLeft(line));
      if (StringLen(line) == 0)
         continue;

      // Heartbeat red
      if (StringFind(line, "HEARTBEAT=") == 0)
      {
         string ts = StringSubstr(line, 10);
         gLastHeartbeat = (datetime)StringToInteger(ts);
         continue;
      }

      // Pozicija red: TICKET|SYMBOL|TYPE|LOTS|OPENPRICE|SL|TP|MAGIC|OPENTIME
      string parts[];
      int n = StringSplit(line, '|', parts);
      if (n < 9)
         continue;

      MasterPos mp;
      mp.ticket    = StringToInteger(parts[0]);
      mp.symbol    = parts[1];
      mp.type      = (int)StringToInteger(parts[2]);
      mp.lots      = StringToDouble(parts[3]);
      mp.openPrice = StringToDouble(parts[4]);
      mp.sl        = StringToDouble(parts[5]);
      mp.tp        = StringToDouble(parts[6]);
      mp.magic     = StringToInteger(parts[7]);
      mp.openTime  = StringToInteger(parts[8]);

      int idx = gMasterCount;
      ArrayResize(gMasterPositions, idx + 1);
      gMasterPositions[idx] = mp;
      gMasterCount++;
   }

   FileClose(handle);
   return true;
}

//+------------------------------------------------------------------+
void SyncPositions()
{
   // 1. Otvori pozicije koje postoje na masteru, a ne na slaveu
   for (int m = 0; m < gMasterCount; m++)
   {
      MasterPos mp = gMasterPositions[m];
      if (!SlaveHasPosition(mp.ticket))
         OpenSlavePosition(mp);
   }

   // 2. Zatvori pozicije koje vise ne postoje na masteru
   for (int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if (!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;
      if (OrderMagicNumber() != MagicNumber)
         continue;

      long masterTicket = GetMasterTicketFromComment(OrderComment());
      if (!MasterStillOpen(masterTicket))
         CloseSlaveOrder(OrderTicket());
   }

   // 3. Azuriraj SL/TP ako se promijenio na masteru
   for (int m = 0; m < gMasterCount; m++)
   {
      MasterPos mp = gMasterPositions[m];
      int slaveTicket = FindSlaveTicket(mp.ticket);
      if (slaveTicket < 0)
         continue;
      if (!OrderSelect(slaveTicket, SELECT_BY_TICKET))
         continue;

      if (MathAbs(OrderStopLoss() - mp.sl) > 0.00001 ||
          MathAbs(OrderTakeProfit() - mp.tp) > 0.00001)
      {
         OrderModify(slaveTicket, OrderOpenPrice(), mp.sl, mp.tp,
                     0, clrYellow);
      }
   }
}

//+------------------------------------------------------------------+
bool SlaveHasPosition(long masterTicket)
{
   for (int i = 0; i < OrdersTotal(); i++)
   {
      if (!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;
      if (OrderMagicNumber() != MagicNumber)
         continue;
      if (GetMasterTicketFromComment(OrderComment()) == masterTicket)
         return true;
   }
   return false;
}

bool MasterStillOpen(long masterTicket)
{
   for (int m = 0; m < gMasterCount; m++)
      if (gMasterPositions[m].ticket == masterTicket)
         return true;
   return false;
}

int FindSlaveTicket(long masterTicket)
{
   for (int i = 0; i < OrdersTotal(); i++)
   {
      if (!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;
      if (OrderMagicNumber() != MagicNumber)
         continue;
      if (GetMasterTicketFromComment(OrderComment()) == masterTicket)
         return OrderTicket();
   }
   return -1;
}

long GetMasterTicketFromComment(string comment)
{
   // Comment format: "SCX#<masterTicket>"
   if (StringFind(comment, "SCX#") < 0)
      return -1;
   string ts = StringSubstr(comment, StringFind(comment, "SCX#") + 4);
   return StringToInteger(ts);
}

//+------------------------------------------------------------------+
void OpenSlavePosition(MasterPos &mp)
{
   int orderType = (mp.type == 0) ? OP_BUY : OP_SELL;
   string comment = "SCX#" + IntegerToString(mp.ticket);

   double price = (orderType == OP_BUY)
                  ? MarketInfo(mp.symbol, MODE_ASK)
                  : MarketInfo(mp.symbol, MODE_BID);

   int ticket = OrderSend(mp.symbol, orderType, mp.lots, price,
                          Slippage, mp.sl, mp.tp,
                          comment, MagicNumber, 0,
                          (orderType == OP_BUY) ? clrGreen : clrRed);

   if (ticket < 0)
      Print("OrderSend greska: ", GetLastError(), " Symbol:", mp.symbol,
            " Lots:", mp.lots, " Price:", price);
   else
      Print("Otvoren slave order: #", ticket, " (master #", mp.ticket, ")");
}

void CloseSlaveOrder(int ticket)
{
   if (!OrderSelect(ticket, SELECT_BY_TICKET))
      return;

   string sym  = OrderSymbol();
   double lots = OrderLots();
   int    type = OrderType();

   double price = (type == OP_BUY)
                  ? MarketInfo(sym, MODE_BID)
                  : MarketInfo(sym, MODE_ASK);

   if (!OrderClose(ticket, lots, price, Slippage, clrOrange))
      Print("OrderClose greska: ", GetLastError(), " ticket:", ticket);
   else
      Print("Zatvoren slave order: #", ticket);
}

//+------------------------------------------------------------------+
void HandleSenderOffline()
{
   if (gSenderOnline)
   {
      Print("UPOZORENJE: MT5 Sender offline!");
      gSenderOnline = false;
   }

   if (CloseIfSenderOffline)
   {
      Print("Zatvaranje svih slave pozicija jer je sender offline...");
      for (int i = OrdersTotal() - 1; i >= 0; i--)
      {
         if (!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
            continue;
         if (OrderMagicNumber() == MagicNumber)
            CloseSlaveOrder(OrderTicket());
      }
   }
}

void OnTick() { OnTimer(); } // Backup: okini i na ticku
//+------------------------------------------------------------------+

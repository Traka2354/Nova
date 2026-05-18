//+------------------------------------------------------------------+
//|  SonicCopyX Sender — MT5 Master EA                              |
//|  Pise pozicije u dijeljeni fajl koji MT4 Receiver cita          |
//+------------------------------------------------------------------+
#property copyright "Sonic AI CopyX"
#property version   "1.00"
#property strict

input string   SignalFile    = "SonicCopyX_signal.csv"; // Ime fajla (Common folder)
input int      TimerMs       = 200;                      // Interval provjere (ms)
input double   LotMultiplier = 1.0;                      // Mnozac lotova (1.0 = isti lot)
input bool     CopyAllSymbols = true;                    // true = svi simboli
input string   AllowedSymbols = "XAUUSD,EURUSD";        // Ako CopyAllSymbols=false

string   gFilePath;
string   gPrevContent = "";

//+------------------------------------------------------------------+
int OnInit()
{
   gFilePath = SignalFile;
   EventSetMillisecondTimer(TimerMs);
   Print("SonicCopyX Sender pokrenut. Fajl: ", gFilePath);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   // Obrisati fajl kad EA stane — receiver ce znati da je sender offline
   FileDelete(gFilePath, FILE_COMMON);
}

//+------------------------------------------------------------------+
void OnTimer()
{
   string content = BuildSignalContent();
   if (content == gPrevContent)
      return; // Nista novo — ne pisati fajl

   WriteSignalFile(content);
   gPrevContent = content;
}

//+------------------------------------------------------------------+
string BuildSignalContent()
{
   string out = "";
   out += "HEARTBEAT=" + IntegerToString((int)TimeCurrent()) + "\n";

   for (int i = 0; i < PositionsTotal(); i++)
   {
      ulong ticket = PositionGetTicket(i);
      if (!PositionSelectByTicket(ticket))
         continue;

      string sym = PositionGetString(POSITION_SYMBOL);

      if (!CopyAllSymbols)
      {
         if (StringFind(AllowedSymbols, sym) < 0)
            continue;
      }

      long   pType   = PositionGetInteger(POSITION_TYPE);    // 0=Buy, 1=Sell
      double lots    = PositionGetDouble(POSITION_VOLUME) * LotMultiplier;
      double open_p  = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl      = PositionGetDouble(POSITION_SL);
      double tp      = PositionGetDouble(POSITION_TP);
      long   magic   = PositionGetInteger(POSITION_MAGIC);
      string comment = PositionGetString(POSITION_COMMENT);
      long   openTime = PositionGetInteger(POSITION_TIME);

      // Format: TICKET|SYMBOL|TYPE|LOTS|OPENPRICE|SL|TP|MAGIC|OPENTIME
      out += IntegerToString((long)ticket) + "|"
           + sym + "|"
           + IntegerToString(pType) + "|"
           + DoubleToString(lots, 2) + "|"
           + DoubleToString(open_p, 5) + "|"
           + DoubleToString(sl, 5) + "|"
           + DoubleToString(tp, 5) + "|"
           + IntegerToString(magic) + "|"
           + IntegerToString(openTime) + "\n";
   }
   return out;
}

//+------------------------------------------------------------------+
void WriteSignalFile(const string content)
{
   int handle = FileOpen(gFilePath, FILE_WRITE | FILE_TXT | FILE_COMMON | FILE_ANSI);
   if (handle == INVALID_HANDLE)
   {
      Print("Greska pri otvaranju fajla: ", GetLastError());
      return;
   }
   FileWriteString(handle, content);
   FileClose(handle);
}

void OnTick() {}
//+------------------------------------------------------------------+

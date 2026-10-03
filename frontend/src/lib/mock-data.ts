export type ChatRole = "user" | "assistant";

export interface TableData {
  columns: string[];
  rows: (string | number)[][];
}

export interface ChartData {
  title: string;
  bars: { label: string; value: number }[];
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  text: string;
  table?: TableData;
  chart?: ChartData;
  code?: string;
  pdfName?: string;
}

export interface Dataset {
  id: string;
  name: string;
  rows: number;
  columns: number;
  size: string;
  uploadedAt: string;
  columnTypes: { name: string; type: "numeric" | "text" | "date" | "category" }[];
  cleaningStatus: "clean" | "warnings" | "issues";
}

export interface Conversation {
  id: string;
  title: string;
  datasetId: string;
  updatedAt: string;
}

export const sampleDataset: Dataset = {
  id: "ds_1",
  name: "orders_q3_2025.csv",
  rows: 48_312,
  columns: 14,
  size: "6.2 MB",
  uploadedAt: "Today, 10:24",
  cleaningStatus: "warnings",
  columnTypes: [
    { name: "order_id", type: "text" },
    { name: "customer_id", type: "text" },
    { name: "order_date", type: "date" },
    { name: "country", type: "category" },
    { name: "category", type: "category" },
    { name: "quantity", type: "numeric" },
    { name: "unit_price", type: "numeric" },
    { name: "discount", type: "numeric" },
    { name: "revenue", type: "numeric" },
    { name: "channel", type: "category" },
  ],
};

export const otherDatasets: Dataset[] = [
  { id: "ds_2", name: "customers_2025.xlsx", rows: 12_044, columns: 9, size: "1.8 MB", uploadedAt: "Yesterday", cleaningStatus: "clean", columnTypes: [] },
  { id: "ds_3", name: "marketing_spend.csv", rows: 2_310, columns: 7, size: "412 KB", uploadedAt: "3 days ago", cleaningStatus: "clean", columnTypes: [] },
];

export const conversations: Conversation[] = [
  { id: "c1", title: "Top categories in Q3", datasetId: "ds_1", updatedAt: "Today" },
  { id: "c2", title: "Discount impact on revenue", datasetId: "ds_1", updatedAt: "Yesterday" },
  { id: "c3", title: "Repeat customer rate", datasetId: "ds_2", updatedAt: "Mon" },
];

export const suggestedQuestions = [
  "What are my top 5 product categories by revenue?",
  "How did revenue trend over the last 90 days?",
  "Which country has the highest average order value?",
  "Is there a correlation between discount and quantity sold?",
  "Show me underperforming SKUs with margin < 10%.",
];

export const initialMessages: ChatMessage[] = [
  {
    id: "m1",
    role: "assistant",
    text: "I analyzed **orders_q3_2025.csv**. It contains 48,312 rows across 14 columns. I detected 3 date columns, 5 numeric metrics, and 2 minor data quality issues (12 null `country` values, 1 outlier in `unit_price`). Ask me anything about your data.",
  },
  {
    id: "m2",
    role: "user",
    text: "What are my top 5 product categories by revenue this quarter?",
  },
  {
    id: "m3",
    role: "assistant",
    text: "Here are the **top 5 categories by revenue** in Q3 2025. Apparel leads with $1.24M, followed by Home & Living. Together the top 5 represent **78% of total revenue**.",
    table: {
      columns: ["Category", "Revenue", "Orders", "AOV"],
      rows: [
        ["Apparel", "$1,243,210", 9_842, "$126.32"],
        ["Home & Living", "$986,540", 7_120, "$138.56"],
        ["Electronics", "$742,118", 3_204, "$231.62"],
        ["Beauty", "$512,990", 6_481, "$79.15"],
        ["Sports", "$398,221", 4_017, "$99.13"],
      ],
    },
    chart: {
      title: "Revenue by category (Q3 2025)",
      bars: [
        { label: "Apparel", value: 1243 },
        { label: "Home & Living", value: 986 },
        { label: "Electronics", value: 742 },
        { label: "Beauty", value: 513 },
        { label: "Sports", value: 398 },
      ],
    },
    code: `SELECT category, SUM(revenue) AS revenue, COUNT(*) AS orders
FROM orders
WHERE order_date BETWEEN '2025-07-01' AND '2025-09-30'
GROUP BY category
ORDER BY revenue DESC
LIMIT 5;`,
    pdfName: "top-categories-q3-2025.pdf",
  },
];

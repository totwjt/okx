import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table';
import { cn } from '../../lib/utils';

export function DataTable<T>({
  data,
  columns,
  emptyText = '暂无数据',
  className,
}: {
  data: T[];
  columns: ColumnDef<T, any>[];
  emptyText?: string;
  className?: string;
}) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className={cn('max-w-full overflow-auto', className)}>
      <table className="w-full min-w-[760px] border-collapse text-left text-sm">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className="border-b border-border text-xs text-muted-foreground">
              {headerGroup.headers.map((header) => (
                <th key={header.id} className="h-10 whitespace-nowrap px-3 font-semibold">
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.length === 0 ? (
            <tr>
              <td className="h-24 px-3 text-center text-muted-foreground" colSpan={columns.length}>
                {emptyText}
              </td>
            </tr>
          ) : (
            table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-b border-border text-foreground last:border-0">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="max-w-[280px] truncate px-3 py-3 align-top">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

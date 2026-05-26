import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

export function NotFoundPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>页面未实现</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">当前路由暂无独立配置项。</CardContent>
    </Card>
  );
}

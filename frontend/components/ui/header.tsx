"use client";

import Link from "next/link";
import { useState, useTransition } from "react"; // <-- ИМПОРТИРУЕМ useTransition
import { useAuth } from "@/context/auth-context";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AuthForm } from "@/components/auth-form";
import { Loader2 } from "lucide-react"; // <-- ИМПОРТИРУЕМ иконку спиннера (если используете lucide-react, который обычно идет с shadcn)
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRouter, usePathname } from "next/navigation";

export function Header() {
  const { isAuthenticated, userEmail, userLevel, logout, updateUserLevel } = useAuth();
  const [isAuthDialogOpen, setIsAuthDialogOpen] = useState(false);
  const [isPending, startTransition] = useTransition(); // <-- ИНИЦИАЛИЗИРУЕМ transition
  const router = useRouter();
  const pathname = usePathname();

  const handleLevelChange = (newLevel: string) => {
    if (userLevel === newLevel) return;

    // Оборачиваем асинхронное действие в startTransition
    startTransition(async () => {
      try {
        await updateUserLevel(newLevel);

        // Проверяем текущий путь
        if (pathname.startsWith('/rules/')) {
          router.push('/');
        } else {
          router.refresh();
        }
      } catch (error) {
        console.error("Failed to update user level:", error);
      }
    });
  };

  const validLevels = ["A1", "A2", "B1", "B2"];

  return (
    <header className="w-full bg-white border-b border-slate-200 py-4 px-4 sm:px-6 shadow-sm">
      <div className="container mx-auto max-w-6xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        {/* Логотип и подпись */}
        <div>
          <Link href="/" passHref className="hover:opacity-90 transition-opacity">
            <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 font-sans">
              Linguaml<span className="text-indigo-600">.</span>
            </h1>
          </Link>
          <p className="text-slate-500 mt-1 text-sm">
            Изучайте испанскую грамматику, адаптированную под ваш уровень.
          </p>
        </div>

        {/* Блок авторизации и уровня пользователя */}
        <div className="flex items-center space-x-4 self-end sm:self-auto">
          {isAuthenticated ? (
              <div className="flex items-center space-x-2 bg-slate-50 p-1.5 pl-3 rounded-xl border border-slate-100 shadow-sm">
                <div className="flex items-center gap-3">
                  {/* Кнопка "Мой Прогресс" */}
                  <Link
                    href="/progress"
                    className="text-sm font-semibold text-slate-600 hover:text-indigo-600 relative py-1 transition-colors after:absolute after:bottom-0 after:left-0 after:h-[2px] after:w-0 hover:after:w-full after:bg-indigo-600 after:transition-all"
                  >
                    Мой Прогресс
                  </Link>

                  {/* Разделитель */}
                  <span className="text-slate-300 text-xs hidden sm:inline">|</span>

                  {/* Приветствие */}
                  <span className="text-sm text-slate-500 hidden md:inline">
                    Привет, <strong className="font-semibold text-slate-700">{userEmail}</strong>
                  </span>

                  {/* Разделитель */}
                  <span className="text-slate-300 text-xs hidden md:inline">|</span>

                  {/* Переключатель уровня пользователя */}
                  <div className="flex items-center gap-2">
                      <Select
                        onValueChange={handleLevelChange}
                        value={userLevel}
                        disabled={isPending}
                      >
                        <SelectTrigger className="w-[85px] h-9 text-sm font-medium bg-white border-slate-200 rounded-lg shadow-sm focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-70 transition-all">
                          <SelectValue placeholder="Уровень" />
                        </SelectTrigger>

                        {/* ИСПРАВЛЕНИЕ: Добавлены position="popper" и sideOffset={4} */}
                        <SelectContent
                          position="popper"
                          sideOffset={4}
                          className="rounded-lg shadow-md min-w-[85px]"
                        >
                          {validLevels.map((level) => (
                            <SelectItem
                              key={level}
                              value={level}
                              className="text-sm font-medium rounded-md focus:bg-indigo-50 focus:text-indigo-600 cursor-pointer"
                            >
                              {level}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      {/* Индикатор загрузки */}
                      {isPending && (
                        <div className="w-4 h-4 flex items-center justify-center">
                          <Loader2 className="h-4 w-4 animate-spin text-indigo-600 dynamic-spinner" />
                        </div>
                      )}
                    </div>
                </div>

                {/* Разделитель перед выходом */}
                <span className="text-slate-200 h-5 w-[1px] mx-1"></span>

                <Button
                  onClick={logout}
                  variant="ghost"
                  className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 rounded-lg h-9 text-sm font-medium transition-colors"
                  disabled={isPending}
                >
                  Выйти
                </Button>
              </div>
            ) : (
            <div className="flex items-center space-x-3">
              <Badge variant="outline" className="text-slate-500 border-slate-300 font-medium">
                Режим гостя (A1)
              </Badge>

              <Dialog open={isAuthDialogOpen} onOpenChange={setIsAuthDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl shadow-sm transition-all text-sm h-10">
                    Войти / Зарегистрироваться
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[425px]">
                  <DialogHeader>
                    <DialogTitle>Вход / Регистрация</DialogTitle>
                    <DialogDescription>
                      Войдите или зарегистрируйтесь, чтобы получить доступ ко всем функциям.
                    </DialogDescription>
                  </DialogHeader>
                  <AuthForm onClose={() => setIsAuthDialogOpen(false)} />
                </DialogContent>
              </Dialog>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
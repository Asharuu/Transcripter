using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;

[assembly: AssemblyTitle("Transcripter")]
[assembly: AssemblyProduct("Transcripter")]
[assembly: AssemblyCompany("Asharuu")]
[assembly: AssemblyDescription("Transcripter - Real-time AI Audio and Meeting Transcription")]
[assembly: AssemblyFileVersion("1.0.0.0")]
[assembly: AssemblyInformationalVersion("1.0.0.0")]

class Program
{
    public const string APP_ID = "Asharuu.Transcripter.Desktop.1.0";

    [STAThread]
    static int Main(string[] args)
    {
        string dir = AppDomain.CurrentDomain.BaseDirectory;

        if (args != null && args.Length > 0 && args[0] == "--install-shortcuts")
        {
            try
            {
                InstallShortcuts(dir);
                Console.WriteLine("Shortcuts installed successfully with AppUserModelID.");
                return 0;
            }
            catch (Exception ex)
            {
                Console.WriteLine("Error installing shortcuts: " + ex.Message);
                return 1;
            }
        }

        string pythonw = Path.Combine(dir, ".venv", "Scripts", "pythonw.exe");
        if (!File.Exists(pythonw))
        {
            pythonw = "pythonw.exe";
        }

        string argStr = "-m src.main";
        if (args != null && args.Length > 0)
        {
            argStr += " " + string.Join(" ", args);
        }

        ProcessStartInfo psi = new ProcessStartInfo
        {
            FileName = pythonw,
            Arguments = argStr,
            WorkingDirectory = dir,
            UseShellExecute = false,
            CreateNoWindow = true
        };

        try
        {
            using (Process p = Process.Start(psi))
            {
                return 0;
            }
        }
        catch
        {
            return 1;
        }
    }

    public static void InstallShortcuts(string projectDir)
    {
        string exePath = Path.Combine(projectDir, "Transcripter.exe");
        string iconPath = Path.Combine(projectDir, "assets", "icon.ico");
        string desktopPath = Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
        string programsPath = Environment.GetFolderPath(Environment.SpecialFolder.Programs);

        CreateShortcut(
            Path.Combine(desktopPath, "Transcripter.lnk"),
            exePath,
            "",
            projectDir,
            iconPath,
            "Transcripter - Real-time AI Audio and Meeting Transcription",
            APP_ID
        );

        CreateShortcut(
            Path.Combine(programsPath, "Transcripter.lnk"),
            exePath,
            "",
            projectDir,
            iconPath,
            "Transcripter - Real-time AI Audio and Meeting Transcription",
            APP_ID
        );

        RegisterAppUserModelId(iconPath);
    }

    [DllImport("shell32.dll")]
    static extern void SHChangeNotify(uint wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);

    private static void RegisterAppUserModelId(string iconPath)
    {
        try
        {
            using (Microsoft.Win32.RegistryKey key = Microsoft.Win32.Registry.CurrentUser.CreateSubKey(@"Software\Classes\AppUserModelId\" + APP_ID))
            {
                if (key != null)
                {
                    key.SetValue("DisplayName", "Transcripter");
                    key.SetValue("IconUri", iconPath);
                    key.SetValue("IconBackgroundColor", "0");
                }
            }

            using (Microsoft.Win32.RegistryKey key = Microsoft.Win32.Registry.CurrentUser.CreateSubKey(@"Software\Classes\Applications\Transcripter.exe"))
            {
                if (key != null)
                {
                    key.SetValue("FriendlyAppName", "Transcripter");
                    using (Microsoft.Win32.RegistryKey iconKey = key.CreateSubKey("DefaultIcon"))
                    {
                        if (iconKey != null)
                        {
                            iconKey.SetValue("", iconPath + ",0");
                        }
                    }
                }
            }

            SHChangeNotify(0x08000000, 0x0000, IntPtr.Zero, IntPtr.Zero);
        }
        catch { }
    }

    private static void CreateShortcut(string shortcutPath, string targetPath, string arguments, string workingDir, string iconPath, string description, string appId)
    {
        IShellLinkW link = (IShellLinkW)new CShellLink();
        link.SetPath(targetPath);
        if (!string.IsNullOrEmpty(arguments)) link.SetArguments(arguments);
        if (!string.IsNullOrEmpty(workingDir)) link.SetWorkingDirectory(workingDir);
        if (!string.IsNullOrEmpty(iconPath) && File.Exists(iconPath)) link.SetIconLocation(iconPath, 0);
        if (!string.IsNullOrEmpty(description)) link.SetDescription(description);

        if (!string.IsNullOrEmpty(appId))
        {
            IPropertyStore store = (IPropertyStore)link;
            PropertyKey pkey = new PropertyKey(new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5);
            PropVariant pv = PropVariant.FromString(appId);
            store.SetValue(ref pkey, ref pv);
            store.Commit();
        }

        IPersistFile file = (IPersistFile)link;
        file.Save(shortcutPath, true);
    }

    [ComImport, Guid("00021401-0000-0000-C000-000000000046"), ClassInterface(ClassInterfaceType.None)]
    class CShellLink { }

    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("000214F9-0000-0000-C000-000000000046")]
    interface IShellLinkW
    {
        void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszFile, int cchMaxPath, out IntPtr pfd, uint fFlags);
        void GetIDList(out IntPtr ppidl);
        void SetIDList(IntPtr pidl);
        void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszName, int cchMaxName);
        void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string pszName);
        void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszDir, int cchMaxPath);
        void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string pszDir);
        void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszArgs, int cchMaxPath);
        void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string pszArgs);
        void GetHotkey(out short pwHotkey);
        void SetHotkey(short wHotkey);
        void GetShowCmd(out int piShowCmd);
        void SetShowCmd(int iShowCmd);
        void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszIconPath, int cchMaxPath, out int piIcon);
        void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string pszIconPath, int iIcon);
        void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string pszPathRel, uint dwReserved);
        void Resolve(IntPtr hwnd, uint fFlags);
        void SetPath([MarshalAs(UnmanagedType.LPWStr)] string pszFile);
    }

    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("0000010B-0000-0000-C000-000000000046")]
    interface IPersistFile
    {
        void GetClassID(out Guid pClassID);
        [PreserveSig]
        int IsDirty();
        void Load([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, uint dwMode);
        void Save([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, [MarshalAs(UnmanagedType.Bool)] bool fRemember);
        void SaveCompleted([MarshalAs(UnmanagedType.LPWStr)] string pszFileName);
        void GetCurFile([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder ppszFileName);
    }

    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")]
    interface IPropertyStore
    {
        uint GetCount(out uint cProps);
        uint GetAt(uint iProp, out PropertyKey pkey);
        uint GetValue(ref PropertyKey key, out PropVariant pv);
        uint SetValue(ref PropertyKey key, ref PropVariant pv);
        uint Commit();
    }

    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    struct PropertyKey
    {
        public Guid fmtid;
        public uint pid;

        public PropertyKey(Guid guid, uint id)
        {
            fmtid = guid;
            pid = id;
        }
    }

    [StructLayout(LayoutKind.Explicit)]
    struct PropVariant
    {
        [FieldOffset(0)] public ushort vt;
        [FieldOffset(8)] public IntPtr pwszVal;

        public static PropVariant FromString(string val)
        {
            PropVariant pv = new PropVariant();
            pv.vt = 31; // VT_LPWSTR
            pv.pwszVal = Marshal.StringToCoTaskMemUni(val);
            return pv;
        }
    }
}


#!/usr/bin/env swift

import Cocoa

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var textView: NSTextView!
    var statusLabel: NSTextField!
    var actionButton: NSButton!
    var process: Process?
    var pipe: Pipe?
    var isRunning = true
    let scriptDir: String
    let action: String
    
    init(scriptDir: String, action: String) {
        self.scriptDir = scriptDir
        self.action = action
        super.init()
    }
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Create window
        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 600, height: 400),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Meeting Notes Processor"
        window.center()
        window.isReleasedWhenClosed = false
        
        // Create content view
        let contentView = NSView(frame: window.contentView!.bounds)
        contentView.autoresizingMask = [.width, .height]
        window.contentView = contentView
        
        // Status label
        statusLabel = NSTextField(labelWithString: "🔄 Processing...")
        statusLabel.font = NSFont.systemFont(ofSize: 14, weight: .semibold)
        statusLabel.frame = NSRect(x: 15, y: 360, width: 570, height: 25)
        statusLabel.autoresizingMask = [.width, .minYMargin]
        contentView.addSubview(statusLabel)
        
        // Scroll view for text
        let scrollView = NSScrollView(frame: NSRect(x: 15, y: 50, width: 570, height: 300))
        scrollView.autoresizingMask = [.width, .height]
        scrollView.hasVerticalScroller = true
        scrollView.borderType = .bezelBorder
        
        textView = NSTextView(frame: scrollView.bounds)
        textView.isEditable = false
        textView.font = NSFont.monospacedSystemFont(ofSize: 11, weight: .regular)
        textView.backgroundColor = NSColor(white: 0.15, alpha: 1.0)
        textView.textColor = NSColor.white
        textView.autoresizingMask = [.width, .height]
        
        scrollView.documentView = textView
        contentView.addSubview(scrollView)
        
        // Action button
        actionButton = NSButton(title: "Cancel", target: self, action: #selector(buttonClicked))
        actionButton.bezelStyle = .rounded
        actionButton.frame = NSRect(x: 485, y: 10, width: 100, height: 30)
        actionButton.autoresizingMask = [.minXMargin, .maxYMargin]
        contentView.addSubview(actionButton)
        
        window.level = .floating  // Keep window on top
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        
        // Start the process
        startProcess()
    }
    
    func startProcess() {
        process = Process()
        pipe = Pipe()
        
        let venvPython = "\(scriptDir)/.venv/bin/python"
        let mainScript = "\(scriptDir)/meetily_capacities_sync.py"
        
        process?.executableURL = URL(fileURLWithPath: venvPython)
        if action == "scan" {
            process?.arguments = [mainScript, "--scan-imports"]
        } else {
            process?.arguments = [mainScript]
        }
        process?.currentDirectoryURL = URL(fileURLWithPath: scriptDir)
        process?.standardOutput = pipe
        process?.standardError = pipe
        
        pipe?.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if let output = String(data: data, encoding: .utf8), !output.isEmpty {
                DispatchQueue.main.async {
                    self?.appendOutput(output)
                }
            }
        }
        
        process?.terminationHandler = { [weak self] _ in
            DispatchQueue.main.async {
                self?.processFinished()
            }
        }
        
        do {
            try process?.run()
        } catch {
            appendOutput("Error starting process: \(error)\n")
            processFinished()
        }
    }
    
    func appendOutput(_ text: String) {
        textView.string += text
        textView.scrollToEndOfDocument(nil)
    }
    
    func processFinished() {
        isRunning = false
        statusLabel.stringValue = "✅ Complete"
        actionButton.title = "Close"
        pipe?.fileHandleForReading.readabilityHandler = nil
    }
    
    @objc func buttonClicked() {
        if isRunning {
            process?.terminate()
            statusLabel.stringValue = "❌ Cancelled"
            isRunning = false
            actionButton.title = "Close"
        } else {
            NSApp.terminate(nil)
        }
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

// Main
let args = CommandLine.arguments
let scriptDir = args.count > 1 ? args[1] : FileManager.default.currentDirectoryPath
let action = args.count > 2 ? args[2] : "scan"

let app = NSApplication.shared
let delegate = AppDelegate(scriptDir: scriptDir, action: action)
app.delegate = delegate
app.run()

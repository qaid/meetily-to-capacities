#!/usr/bin/env swift

import Cocoa
import Foundation

// MARK: - Data Models

struct PendingRecording {
    let path: String
    let name: String
    let date: Date?
}

// MARK: - App Delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var textView: NSTextView!
    var statusLabel: NSTextField!
    var process: Process?
    var pipe: Pipe?
    var isRunning = false
    let scriptDir: String
    
    // Form controls
    var formContainer: NSView!
    var recordingLabel: NSTextField!
    var typePopup: NSPopUpButton!
    var participantsField: NSTextField!
    var jargonField: NSTextField!
    var processButton: NSButton!
    var skipButton: NSButton!
    var closeButton: NSButton!
    
    // State
    var pendingRecordings: [PendingRecording] = []
    var currentRecordingIndex = 0
    
    init(scriptDir: String) {
        self.scriptDir = scriptDir
        super.init()
    }
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.activate(ignoringOtherApps: true)
        createAndShowWindow()
        scanForRecordings()
    }
    
    func createAndShowWindow() {
        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 700, height: 550),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Meeting Notes Processor"
        window.center()
        window.isReleasedWhenClosed = false
        
        let contentView = NSView(frame: window.contentView!.bounds)
        contentView.autoresizingMask = [.width, .height]
        window.contentView = contentView
        
        // Status label at top
        statusLabel = NSTextField(labelWithString: "🔍 Scanning for new recordings...")
        statusLabel.font = NSFont.systemFont(ofSize: 14, weight: .semibold)
        statusLabel.frame = NSRect(x: 15, y: 515, width: 670, height: 25)
        statusLabel.autoresizingMask = [.width, .minYMargin]
        contentView.addSubview(statusLabel)
        
        // Form container (hidden initially)
        formContainer = NSView(frame: NSRect(x: 15, y: 360, width: 670, height: 145))
        formContainer.autoresizingMask = [.width, .minYMargin]
        formContainer.isHidden = true
        contentView.addSubview(formContainer)
        
        // Recording name
        recordingLabel = NSTextField(labelWithString: "")
        recordingLabel.font = NSFont.systemFont(ofSize: 13, weight: .medium)
        recordingLabel.frame = NSRect(x: 0, y: 120, width: 670, height: 20)
        recordingLabel.lineBreakMode = .byTruncatingMiddle
        formContainer.addSubview(recordingLabel)
        
        // Recording Type row
        let typeLabel = NSTextField(labelWithString: "Type:")
        typeLabel.frame = NSRect(x: 0, y: 88, width: 100, height: 20)
        formContainer.addSubview(typeLabel)
        
        typePopup = NSPopUpButton(frame: NSRect(x: 105, y: 83, width: 280, height: 30))
        typePopup.addItems(withTitles: ["Meeting", "Summary (Documentary/Talk/Essay)"])
        formContainer.addSubview(typePopup)
        
        // Participants row
        let participantsLabel = NSTextField(labelWithString: "Participants:")
        participantsLabel.frame = NSRect(x: 0, y: 55, width: 100, height: 20)
        formContainer.addSubview(participantsLabel)
        
        participantsField = NSTextField(frame: NSRect(x: 105, y: 52, width: 450, height: 24))
        participantsField.placeholderString = "John, Sarah, Mike (comma separated, optional)"
        participantsField.isEditable = true
        participantsField.isSelectable = true
        participantsField.isBezeled = true
        participantsField.bezelStyle = .roundedBezel
        participantsField.cell?.isScrollable = true
        formContainer.addSubview(participantsField)
        
        // Jargon row
        let jargonLabel = NSTextField(labelWithString: "Product/Jargon:")
        jargonLabel.frame = NSRect(x: 0, y: 22, width: 100, height: 20)
        formContainer.addSubview(jargonLabel)
        
        jargonField = NSTextField(frame: NSRect(x: 105, y: 19, width: 450, height: 24))
        jargonField.placeholderString = "Acme, ProjectX (terms that may be misheard, optional)"
        jargonField.isEditable = true
        jargonField.isSelectable = true
        jargonField.isBezeled = true
        jargonField.bezelStyle = .roundedBezel
        jargonField.cell?.isScrollable = true
        formContainer.addSubview(jargonField)
        
        // Buttons
        processButton = NSButton(title: "Process", target: self, action: #selector(processClicked))
        processButton.bezelStyle = .rounded
        processButton.frame = NSRect(x: 455, y: 83, width: 100, height: 30)
        processButton.keyEquivalent = "\r"
        formContainer.addSubview(processButton)
        
        skipButton = NSButton(title: "Skip", target: self, action: #selector(skipClicked))
        skipButton.bezelStyle = .rounded
        skipButton.frame = NSRect(x: 560, y: 83, width: 80, height: 30)
        formContainer.addSubview(skipButton)
        
        // Scroll view for output (below form)
        let scrollView = NSScrollView(frame: NSRect(x: 15, y: 50, width: 670, height: 300))
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
        
        // Close button at bottom
        closeButton = NSButton(title: "Close", target: self, action: #selector(closeClicked))
        closeButton.bezelStyle = .rounded
        closeButton.frame = NSRect(x: 585, y: 10, width: 100, height: 30)
        closeButton.autoresizingMask = [.minXMargin, .maxYMargin]
        contentView.addSubview(closeButton)
        
        window.level = .floating
        window.makeKeyAndOrderFront(nil)
        
        // Ensure the app can receive keyboard input
        NSApp.setActivationPolicy(.regular)
        
        // Add Edit menu for copy/paste support
        let mainMenu = NSMenu()
        let editMenuItem = NSMenuItem()
        editMenuItem.submenu = NSMenu(title: "Edit")
        editMenuItem.submenu?.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenuItem.submenu?.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenuItem.submenu?.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenuItem.submenu?.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        mainMenu.addItem(editMenuItem)
        NSApp.mainMenu = mainMenu
    }
    
    func scanForRecordings() {
        appendOutput("🔍 Scanning for new recordings...\n\n")
        
        // Load processed files
        let syncStateFile = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".meeting_notes_sync.json")
        var processedFiles: Set<String> = []
        
        if let data = try? Data(contentsOf: syncStateFile),
           let files = try? JSONDecoder().decode([String].self, from: data) {
            processedFiles = Set(files)
        }
        
        // Load transcript directory from .env
        let envFile = URL(fileURLWithPath: scriptDir).appendingPathComponent(".env")
        var transcriptDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Movies/meetily-recordings").path
        
        if let envContent = try? String(contentsOf: envFile, encoding: .utf8) {
            for line in envContent.components(separatedBy: .newlines) {
                if line.hasPrefix("TRANSCRIPT_DIR=") {
                    var value = String(line.dropFirst("TRANSCRIPT_DIR=".count))
                    value = value.trimmingCharacters(in: CharacterSet(charactersIn: "\"'"))
                    if value.hasPrefix("~") {
                        value = FileManager.default.homeDirectoryForCurrentUser.path + String(value.dropFirst())
                    }
                    transcriptDir = value
                    break
                }
            }
        }
        
        appendOutput("📂 Checking: \(transcriptDir)\n\n")
        
        // Scan for Meetily folders
        let transcriptURL = URL(fileURLWithPath: transcriptDir)
        if let contents = try? FileManager.default.contentsOfDirectory(
            at: transcriptURL,
            includingPropertiesForKeys: [.isDirectoryKey, .creationDateKey],
            options: [.skipsHiddenFiles]
        ) {
            for item in contents {
                guard (try? item.resourceValues(forKeys: [.isDirectoryKey]))?.isDirectory == true else { continue }
                
                let transcriptsFile = item.appendingPathComponent("transcripts.json")
                let metadataFile = item.appendingPathComponent("metadata.json")
                
                guard FileManager.default.fileExists(atPath: transcriptsFile.path),
                      FileManager.default.fileExists(atPath: metadataFile.path) else { continue }
                
                // Check if completed
                if let metaData = try? Data(contentsOf: metadataFile),
                   let meta = try? JSONSerialization.jsonObject(with: metaData) as? [String: Any],
                   meta["status"] as? String == "completed" {
                    
                    if !processedFiles.contains(item.path) {
                        let creationDate = (try? item.resourceValues(forKeys: [.creationDateKey]))?.creationDate
                        pendingRecordings.append(PendingRecording(
                            path: item.path,
                            name: item.lastPathComponent,
                            date: creationDate
                        ))
                    }
                }
            }
        }
        
        // Also check import folder
        let importDir = transcriptURL.appendingPathComponent("imported")
        let audioExtensions = ["mp3", "wav", "m4a", "aac", "ogg", "flac", "mp4", "mov", "avi", "mkv", "webm"]
        
        if let importContents = try? FileManager.default.contentsOfDirectory(
            at: importDir,
            includingPropertiesForKeys: [.creationDateKey],
            options: [.skipsHiddenFiles]
        ) {
            for item in importContents {
                if audioExtensions.contains(item.pathExtension.lowercased()) {
                    if !processedFiles.contains(item.path) {
                        let creationDate = (try? item.resourceValues(forKeys: [.creationDateKey]))?.creationDate
                        pendingRecordings.append(PendingRecording(
                            path: item.path,
                            name: item.lastPathComponent,
                            date: creationDate
                        ))
                    }
                }
            }
        }
        
        if pendingRecordings.isEmpty {
            appendOutput("✅ No new recordings to process.\n")
            statusLabel.stringValue = "✅ No new recordings found"
            formContainer.isHidden = true
        } else {
            appendOutput("📋 Found \(pendingRecordings.count) new recording(s):\n")
            for (i, rec) in pendingRecordings.enumerated() {
                appendOutput("   \(i + 1). \(rec.name)\n")
            }
            appendOutput("\n")
            
            // Show form for first recording
            currentRecordingIndex = 0
            showFormForCurrentRecording()
        }
    }
    
    func showFormForCurrentRecording() {
        guard currentRecordingIndex < pendingRecordings.count else {
            formContainer.isHidden = true
            statusLabel.stringValue = "✅ All recordings processed"
            appendOutput("\n✅ All recordings processed or skipped.\n")
            return
        }
        
        let recording = pendingRecordings[currentRecordingIndex]
        let remaining = pendingRecordings.count - currentRecordingIndex
        
        statusLabel.stringValue = "📋 \(remaining) recording(s) to process"
        recordingLabel.stringValue = "📁 \(recording.name)"
        
        // Reset form fields
        typePopup.selectItem(at: 0)
        participantsField.stringValue = ""
        jargonField.stringValue = ""
        
        formContainer.isHidden = false
        processButton.isEnabled = true
        skipButton.isEnabled = true
        
        window.makeFirstResponder(participantsField)
    }
    
    @objc func processClicked() {
        guard currentRecordingIndex < pendingRecordings.count else { return }
        
        let recording = pendingRecordings[currentRecordingIndex]
        let selectedType = typePopup.indexOfSelectedItem == 0 ? "meeting" : "summary"
        let participants = participantsField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        let jargon = jargonField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        
        // Disable form while processing
        processButton.isEnabled = false
        skipButton.isEnabled = false
        formContainer.isHidden = true
        
        processRecording(recording, type: selectedType, participants: participants, jargon: jargon)
    }
    
    @objc func skipClicked() {
        appendOutput("⏭️ Skipped: \(pendingRecordings[currentRecordingIndex].name)\n")
        currentRecordingIndex += 1
        showFormForCurrentRecording()
    }
    
    @objc func closeClicked() {
        if isRunning {
            process?.terminate()
            appendOutput("\n❌ Processing cancelled.\n")
        }
        NSApp.terminate(nil)
    }
    
    func processRecording(_ recording: PendingRecording, type: String, participants: String, jargon: String) {
        isRunning = true
        statusLabel.stringValue = "🔄 Processing: \(recording.name)"
        closeButton.title = "Cancel"
        
        // Build context string
        var contextParts: [String] = []
        if !participants.isEmpty {
            contextParts.append("Participants: \(participants)")
        }
        if !jargon.isEmpty {
            contextParts.append("Product names and jargon to recognize: \(jargon)")
        }
        let context = contextParts.joined(separator: ". ")
        
        appendOutput("\n" + String(repeating: "=", count: 60) + "\n")
        appendOutput("🎬 Processing: \(recording.name)\n")
        appendOutput("📋 Type: \(type)\n")
        if !context.isEmpty {
            appendOutput("📝 Context: \(context)\n")
        }
        appendOutput(String(repeating: "=", count: 60) + "\n\n")
        
        // Start process
        process = Process()
        pipe = Pipe()
        
        let venvPython = "\(scriptDir)/.venv/bin/python"
        let mainScript = "\(scriptDir)/meetily_capacities_sync.py"
        
        process?.executableURL = URL(fileURLWithPath: venvPython)
        
        var args = [mainScript, recording.path, "--type", type]
        if !context.isEmpty {
            args.append("--context")
            args.append(context)
        }
        
        process?.arguments = args
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
        
        process?.terminationHandler = { [weak self] proc in
            DispatchQueue.main.async {
                self?.processFinished(exitCode: proc.terminationStatus)
            }
        }
        
        do {
            try process?.run()
        } catch {
            appendOutput("❌ Error starting process: \(error)\n")
            processFinished(exitCode: 1)
        }
    }
    
    func appendOutput(_ text: String) {
        textView.string += text
        textView.scrollToEndOfDocument(nil)
    }
    
    func processFinished(exitCode: Int32) {
        isRunning = false
        pipe?.fileHandleForReading.readabilityHandler = nil
        closeButton.title = "Close"
        
        let recording = pendingRecordings[currentRecordingIndex]
        
        if exitCode == 0 {
            appendOutput("\n✅ Successfully processed: \(recording.name)\n")
        } else {
            appendOutput("\n❌ Failed to process: \(recording.name)\n")
        }
        
        // Move to next recording
        currentRecordingIndex += 1
        
        if currentRecordingIndex < pendingRecordings.count {
            appendOutput("\n" + String(repeating: "-", count: 60) + "\n")
            showFormForCurrentRecording()
        } else {
            statusLabel.stringValue = "✅ All recordings processed"
            formContainer.isHidden = true
        }
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

// MARK: - Main

let args = CommandLine.arguments
let scriptDir = args.count > 1 ? args[1] : FileManager.default.currentDirectoryPath

let app = NSApplication.shared
let delegate = AppDelegate(scriptDir: scriptDir)
app.delegate = delegate
app.run()
